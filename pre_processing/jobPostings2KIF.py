import os
import requests
import json

def jobPostings2KIF():
    directory = 'datasets/pre-processed/jobPostings'
    url = 'https://magicloops.dev/api/loop/b980e12b-8672-4288-974a-e07dcb8082c2/run'

    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            filepath = os.path.join(directory, filename)

            with open(filepath, 'r') as file:
                content = file.read()

            payload = {'input': content}
            response = requests.post(url, json=payload)
            response_data = response.json()
            output_file_path = os.path.join(directory, f'KIF_{filename[:-4]}.json')
            print(f"\n===================================================================\n")
            print(f"job posing saved to {output_file_path}")

            with open(output_file_path, 'w') as json_file:
                json.dump(response_data, json_file, indent=4)

        else:
            print(f"No .txt files found in {directory} to process.")
            exit()

jobPostings2KIF()
