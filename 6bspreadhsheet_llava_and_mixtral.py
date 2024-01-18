import base64
import requests
from dotenv import load_dotenv
import os
import gspread
from loguru import logger
import time
from openai import OpenAI
import json

def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

def call_gpt_text(text):

    client = OpenAI(base_url="http://192.168.1.191:1235/v1", api_key="not-needed")

    completion = client.chat.completions.create(
      model="local-model",
      messages=[
        {
            "role": "user", 
            "content": text
        }
      ]
    )

    message = completion.choices[0].message
    content = message.content
    return content

def call_gpt_vision(image_path, text):
    base64_image = encode_image(image_path)

    # client = OpenAI(base_url="http://192.168.1.191:1234/v1", api_key="not-needed")
    client = OpenAI(base_url="http://192.168.1.191:1234/v1")

    completion = client.chat.completions.create(
    model="local-model", # not used
    messages=[
        {
        "role": "user",
        "content": [
            # {"type": "text", "text": "What’s in this image?"},
            {"type": "text", "text": text},
            {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            },
            },
        ],
        }
    ],
    # https://platform.openai.com/docs/api-reference/chat/create#chat-create-response_format
    response_format="json_object",
    max_tokens=2000,
    stream=True
    )

    content = ""
    for chunk in completion:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="",flush=True)
            content = content + chunk.choices[0].delta.content

    return content

   
def main():
    logger.add("logs/1trace.log", level="TRACE", rotation="00:00")

    # note 0 based when using get_all_values as referencing a python list
    # for writing using gspread I have to add 1
    entry_number_column_index = 0
    llm_violence_column_index = 4
    llm_5_words_column_index = 5
    llm_1_sentence_column_index = 6
    llm_full_column_index = 7
    archive_status_column_index = 9

    # read Entry Number from spreadsheet
    # look for directory with same name
    # send image to be analysed to llava
    # write result to spreadsheet
    # send result to Mixtral to get rating

    # 1.spreadsheeet
    # Authenticate using the JSON key file
    gc = gspread.service_account(filename='secrets/service_account.json')

    spreadsheet_title = 'AA Demo Main'

    sh = gc.open(spreadsheet_title)

    worksheet = sh.sheet1

    # get all values - so we don't do calls on each row
    all_values = worksheet.get_all_values()

    # iterate over each Entry Number eg DM001
    row_index = 1
    for row in all_values[1:]: # skip first row which is the header
        entry_number = row[entry_number_column_index]
        row_index = row_index + 1

        if entry_number is None or entry_number == "":
            # logger.debug(f'ignoring row as no entry number: {row_index}')
            continue

        # only process if archiver status is blank
        archive_status = row[archive_status_column_index]
        if archive_status is None or archive_status == "": 
            pass
        else:
            # logger.debug(f'ignoring row: {row_index}')
            continue

        # does a directory exist with this name?
        subdirectory = f'pics/{entry_number}'
        if not os.path.exists(subdirectory) or not os.path.isdir(subdirectory):
            # logger.debug(f"The specified path is not a valid directory: {subdirectory}")
            continue # the for loop
            
        logger.info(f'row_index: {row_index} entry_number: {entry_number}')

        files = []
        for f in os.listdir(subdirectory):
            if os.path.isfile(os.path.join(subdirectory, f)):
                if f.lower().endswith('.jpg'):
                    files.append(f)

        # Iterate over each image file in the subdirectory
        for file in files:
            logger.debug(f'Calling LLaVA to analyse this image {file} for Entry Number {entry_number}')
            
            # Path and filename
            image_path = subdirectory + '/' + file

            text = """
Describe this photo in detail. It is taken Myanmar and we are looking for evidence of human rights suffering.
"""

            gpt_vision_result = call_gpt_vision(image_path, text)

            # 1.get description from LLaVA
            current_value = worksheet.cell(row_index, llm_full_column_index+1).value
            new_value = ""
            if current_value:
                new_value = current_value + '\n---' + gpt_vision_result
            else:
                new_value = gpt_vision_result 

            # append filename to long description
            new_value = new_value + f" {file}"

            worksheet.update_cell(row_index, llm_full_column_index +1, new_value)

            # 2. Mixtral
            text = f"""

Given this text below in quotes which describes a photo

Give a rating from 1 to 5 as to how sensitive / traumatic / violence level for a person to look at it would be.

show me step by step why you got this number

"{gpt_vision_result}"

give a summary in less than 9 words

please output as json with headings of: rating, summary
"""
            gpt_text_result = call_gpt_text(text)

            # for conversion to work I need to 
            # strip off ```json at start
            # strip off ``` at end
            foo = gpt_text_result.replace("```json\n", "", 1)
            foo = foo.replace("```", "", 1)

            try:
                data = json.loads(foo)
            except Exception as e:
                logger.error(e)
                logger.error("json decode error")
                continue

            rating = str(data["rating"])
            logger.debug(f"rating is {rating}")
            if rating == "":
                logger.error("blank rating -failing and going to next image")
                continue
            summary = data["summary"]
            logger.debug(f"summary is {summary}")
            if summary == "":
                logger.error("blank summary -failing and going to next image")
                continue
         
            # 2. rating
            current_value = worksheet.cell(row_index, llm_violence_column_index+1).value

            new_value = ""
            if current_value:
                new_value = current_value + '\n\n' + rating
            else:
                new_value = rating

            worksheet.update_cell(row_index, llm_violence_column_index+1, new_value)

            # 3. summary
            current_value = worksheet.cell(row_index, llm_5_words_column_index+1).value

            new_value = ""
            if current_value:
                new_value = current_value + '\n\n' + summary
            else:
                new_value = summary

            worksheet.update_cell(row_index, llm_5_words_column_index+1, new_value)
            continue


            # text = "describe this image in 5 words"
            # gpt_result = call_gpt_vision(image_path, text)

            # logger.debug(f'5 words result: {}')

            current_value = worksheet.cell(row_index, llm_5_words_column_index+1).value

            # current_value = row[llm_5_words_column_index]
            new_value = ""
            foo = ""
            if current_value:
                new_value = current_value + '\n\n' + foo + shortsummary
            else:
                new_value = foo + shortsummary

            # TODO batch_update
            worksheet.update_cell(row_index, llm_5_words_column_index+1, new_value)

            # 3. Describe in 1 sentence - description
            # text = "describe this image in 1 sentence"
            # gpt_result = call_gpt_vision(image_path, text)

            # logger.debug(f'describe this image in 1 sentence: {gpt_result}')

            current_value = worksheet.cell(row_index, llm_1_sentence_column_index+1).value
            new_value = ""
            foo = ""
            if current_value:
               new_value = current_value + '\n\n' + foo + summary
            else:
               new_value = foo + summary

            worksheet.update_cell(row_index, llm_1_sentence_column_index+1, new_value)


if __name__ == "__main__":
    main()
