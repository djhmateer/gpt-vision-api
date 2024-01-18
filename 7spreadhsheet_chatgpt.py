import base64
from dotenv import load_dotenv
import os
import gspread
from loguru import logger
from openai import OpenAI
import json

def call_gpt_vision(image_path, text):
    load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY')

    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    # Getting the base64 string
    base64_image = encode_image(image_path)

    # do I even need the api key?
    client = OpenAI(api_key=api_key)

    completion = client.chat.completions.create(
    model="gpt-4-vision-preview", 
    messages=[
        {
        "role": "user",
        "content": [
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
    # response_format="json_object",
    # max_tokens=2000,
    max_tokens=600,
    stream=True
    )

    content = ""
    for chunk in completion:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="",flush=True)
            content = content + chunk.choices[0].delta.content

    logger.debug(content)
    return content

def main():
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
    # send image to be analysed
    # write result to spreadsheet

    # 1.spreadsheeet
    # Authenticate using the JSON key file
    gc = gspread.service_account(filename='secrets/service_account.json')

    # Open the spreadsheet by its title or URL
    spreadsheet_title = 'AA Demo Main'

    sh = gc.open(spreadsheet_title)

    worksheet = sh.sheet1

    # Read data from the worksheet
    # get all values - so we don't do calls on each row
    all_values = worksheet.get_all_values()


    # iterate over each Entry Number
    row_index = 1
    # for entry_number in entry_numbers[1:6]: # skip first row which is the header, and slice.. gives up to 004
    for row in all_values[1:]: # skip first row which is the header, and slice
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

        logger.info(f'row_index: {row_index} entry_number: {entry_number}')

        # does a directory exist with this name?
        subdirectory = f'pics/{entry_number}'
        if not os.path.exists(subdirectory) or not os.path.isdir(subdirectory):
            # logger.debug(f"The specified path is not a valid directory: {subdirectory}")
            continue # the for loop
            
        files = []
        for f in os.listdir(subdirectory):
            if os.path.isfile(os.path.join(subdirectory, f)):
                if f.lower().endswith('.jpg'):
                    files.append(f)

        # Iterate over each image file in the subdirectory
        for file in files:
            logger.debug(f'Calling ChatGPT-4 to analyse this image {file} for Entry Number {entry_number}')
            
            # Path and filename
            image_path = subdirectory + '/' + file

            # 1. Traumatic Violence Level

#Foo1
            text = """

You are a senior human rights investigator.

You are investigating war crimes and human rights violations in myanmar.

Analyse this photo and give a long summary of it. You should focus on anything to do with human rights eg war, guns, blood, destruction


Give a rating from 1 to 5 as to how sensitive / traumatic / violence level for a person to look at it would be.

For example an image with human deaths or graphic human suffering would be a 5 (very severe), burned out village with property damage would be a 3,
 destroyed buildings 3, whereas an landscape scene / nothing traumatic would be a 1 (no violence), civilian equipment eg a crane would be a 1.
   Only give a high rating if it is truly horrible or traumatic - ie a 5 should only be given for human remains etc..


Use clear and concise non emotive language in formal tone.

Output in a valid json format with header: rating, summary, shortsummary
"""

# Lets think step by step, and give a detailed reason why you gave a rating. Put this into the stepbystep output.

        # Foo2
            # text = """
            # Describe in detail what you see in this image. You are a human rights investigator. This image is from a war torn part of the world
            # """

            gpt_result = call_gpt_vision(image_path, text)

            # logger.debug(f'llm violence result is {gpt_result}')

            # # put into LLM full column for testing
            # # maybe another model is better at doing 1 - 5 violence level eg mixtral 7b
            # worksheet.update_cell(row_index, llm_full_column_index +1, gpt_result)
            # continue
        #Foo2 end


            # Convert to GPT-4 output to Python dictionary

            # for conversion to work I need to 
            # strip off ```json at start
            # strip off ``` at end
            foo = gpt_result.replace("```json\n", "", 1)
            foo = foo.replace("```", "", 1)
            
            try:
              data = json.loads(foo)
            except:
                logger.error("Can' decode json")
                continue

            rating = str(data["rating"])
            summary = data["summary"]
            # shortsummary = data["shortsummary"]
            shortsummary = data.get('shortsummary', '')

            # 1.violence level
            current_value = worksheet.cell(row_index, llm_violence_column_index+1).value

            new_value = ""
            foo = ""
            if current_value:
                new_value = current_value + '\n\n' + foo + rating
            else:
                new_value = foo + rating
            worksheet.update_cell(row_index, llm_violence_column_index+1, new_value)

            # 2. Describe in 5 words
            current_value = worksheet.cell(row_index, llm_5_words_column_index+1).value
            new_value = ""
            foo = ""
            if current_value:
                new_value = current_value + '\n\n' + foo + shortsummary
            else:
                new_value = foo + shortsummary
            new_value = new_value + f" ({file})" 

            worksheet.update_cell(row_index, llm_5_words_column_index+1, new_value)

            # 3. Describe in 1 sentence
            current_value = worksheet.cell(row_index, llm_1_sentence_column_index+1).value
            new_value = ""
            foo = ""
            if current_value:
               new_value = current_value + '\n---\n' + foo + summary
            else:
               new_value = foo + summary
            new_value = new_value + f" ({file})" 

            worksheet.update_cell(row_index, llm_1_sentence_column_index+1, new_value)

if __name__ == "__main__":
    logger.add("logs/0trace.log", level="TRACE", rotation="00:00")
    main()
