import os
import requests
import json

def applicants2KIF():
    directory = 'datasets/pre-processed/applicants'
    url = 'https://magicloops.dev/api/loop/ac09bad0-7a44-46c2-89f5-d881f5c20a64/run'

    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            filepath = os.path.join(directory, filename)

            with open(filepath, 'r') as file:
                content = file.read()

            payload = {'input': content}
            response = requests.post(url, json=payload)
            response_data = response.json()
            output_file_path = os.path.join(directory, f'KIF_{filename[:-4]}.json')
            print(f"applicant saved to {output_file_path}")

            with open(output_file_path, 'w') as json_file:
                json.dump(response_data, json_file, indent=4)

        else:
            print(f"No .txt files found in {directory} to process.")
            exit()

applicants2KIF()
