import base64
import requests
from dotenv import load_dotenv
import os
import gspread
from loguru import logger

def call_gpt_vision(image_path, text):
    load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY')
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    # Getting the base64 string
    base64_image = encode_image(image_path)

    headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
    }


    payload = {
    "model": "gpt-4-vision-preview",
    "messages": [
        {
        "role": "user",
        "content": [
            {
            "type": "text",
            # "text": "What’s in this image?"
            "text": text
            },
            {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
            }
        ]
        }
    ],
    "max_tokens": 300
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    foo = response.json()
    content = foo['choices'][0]['message']['content']
    # probable: Policy Restrictions: OpenAI has strict policies about the types of requests it can fulfill, especially regarding privacy, ethical considerations, and copyright. If your request potentially violates any of these policies, the API will decline to process it.
    # if content == "I'm sorry, I cannot provide this service.":
        # logger.error('caught')
        
    # what does this mean while calling the gpt api: I'm sorry, I can't assist with this request.
    # Privacy Concerns: Involves personal data or confidentiality issues.
    #Illegal Activities: Any actions that are illegal or encourage illegality.
    #Harmful Actions: Potential harm to individuals, animals, or the environment.
    #Discriminatory Content: Hate, abuse, or discrimination against any group.
    #Deception: Misinformation, scams, or other manipulative practices.
    #Explicit Material: Adult content or graphic violence.
    #Beyond Capabilities: Requests that the model cannot technically fulfill.
    # if content == "I'm sorry, I can't assist with this request.":
        # logger.error('caught')

    # it can produce many very similar errors
    if "I'm sorry, " in content:
        logger.error('Chat GPT Error caught')

    return content


def main():
    logger.add("logs/1trace.log", level="TRACE", rotation="00:00")

    # note 0 based when using get_all_values as referencing a python list
    # for writing using gspread I have to add 1
    entry_number_column_index = 0
    llm_violence_column_index = 4
    llm_5_words_column_index = 5
    llm_1_sentence_column_index = 6
    archive_status_column_index = 8
    
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
    # values_list = worksheet.row_values(1)  # Get the first row
    # print(values_list)

    # get all values - so we don't do calls on each row
    all_values = worksheet.get_all_values()


    # Get all values from the specified column
    # entry_numbers = worksheet.col_values(entry_number_column_index)

    # iterate over each Entry Number
    row_index = 1
    # for entry_number in entry_numbers[1:6]: # skip first row which is the header, and slice.. gives up to 004
    for row in all_values[1:]: # skip first row which is the header, and slice.. gives up to 004
        entry_number = row[entry_number_column_index]
        row_index = row_index + 1

        if entry_number is None or entry_number == "":
            logger.debug(f'ignoring row as no entry number: {row_index}')
            continue



        # only process if archiver status is blank
        # archive_status = worksheet.cell(row_index, archive_status_column_index).value
        archive_status = row[archive_status_column_index]
        if archive_status is None or archive_status == "": 
            pass
        else:
            logger.debug(f'ignoring row: {row_index}')
            continue



        logger.info(f'row_index: {row_index} entry_number: {entry_number}')

        # does a directory exist with this name?
        subdirectory = f'pics/{entry_number}'
        if not os.path.exists(subdirectory) or not os.path.isdir(subdirectory):
            logger.debug(f"The specified path is not a valid directory: {subdirectory}")
            continue # the for loop
            
        files = []
        for f in os.listdir(subdirectory):
            if os.path.isfile(os.path.join(subdirectory, f)):
                if f.lower().endswith('.jpg'):
                    files.append(f)

        # Iterate over each image file in the subdirectory
        for file in files:
            logger.debug(f'Calling ChatGPT to analyse this image {file} for Entry Number {entry_number}')
            
            # Path and filename
            image_path = subdirectory + '/' + file

            # 1. Traumatic Violence Level
            # text = "Tell me if this would be classified as a traumatic picture for someone to look at. give traumatic rating on a scale of 1 - 5. Just return the number and no other text"
            # text = "Is this a potentially sensitive picture?"
            # text = "Is this a sensitive picture? only return 10 words summary. Also give a rating from 1 to 5 as to how sensitive it is please."
            text = "Is this a sensitive picture? please give 1 word summary. give a rating from 1 to 5 as to how sensitive it is please. summerise in 1 sentence "
            gpt_result = call_gpt_vision(image_path, text)

            logger.debug(f'llm violence result is {gpt_result}')

            # append to the cell (for the case of multiple photos)
            current_value = worksheet.cell(row_index, llm_violence_column_index+1).value
            # current_value = row[llm_violence_column_index]
            new_value = ""
            if current_value:
                new_value = current_value + '\n\n' + gpt_result
            else:
                new_value = gpt_result

            # TODO batch_update
            worksheet.update_cell(row_index, llm_violence_column_index+1, new_value)

            # hack to only work on the violence level
            continue

            # 2. Describe in 5 words
            text = "describe this image in 5 words"
            gpt_result = call_gpt_vision(image_path, text)

            logger.debug(f'5 words result: {gpt_result}')

            current_value = worksheet.cell(row_index, llm_5_words_column_index+1).value
            # current_value = row[llm_5_words_column_index]
            new_value = ""
            if current_value:
                new_value = current_value + '\n' + gpt_result
            else:
                new_value = gpt_result

            # TODO batch_update
            worksheet.update_cell(row_index, llm_5_words_column_index+1, new_value)


            # 3. Describe in 1 sentence
            text = "describe this image in 1 sentence"
            gpt_result = call_gpt_vision(image_path, text)

            logger.debug(f'describe this image in 1 sentence: {gpt_result}')

            current_value = worksheet.cell(row_index, llm_1_sentence_column_index+1).value
            new_value = ""
            if current_value:
                new_value = current_value + '\n' + gpt_result
            else:
                new_value = gpt_result

            # TODO batch_update
            worksheet.update_cell(row_index, llm_1_sentence_column_index+1, new_value)



            
            # text = "describe this image in 5 words"

            # text = "describe this image in 1 sentence"

            # 5 words
            # Flowering chestnut tree in bloom
            # Chestnut flowers blooming in spring
            # Flowering tree, white blooms, greenery.
            # Chestnut tree blooming in spring.

            # 1 sentence
            # A cluster of delicate white flowers with pink speckles and prominent stamens is surrounded by green leaves under a canopy of trees.

            # trauma
            # 1

            # print(content)

if __name__ == "__main__":
    main()
