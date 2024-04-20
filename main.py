# main.py pdf summary endpoint

from flask import Flask, request, jsonify
import os
import pdfplumber
import openai
import glob2
import textwrap


def open_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as infile:
            return str.strip(infile.read())
    except Exception as e:
        print(f"An error occurred while opening the file '{filepath}': {str(e)}")
        return None  # Return None if an error occurs


def save_file(filepath, content):
    try:
        with open(filepath, 'w', encoding='utf-8') as outfile:
            outfile.write(content)
    except Exception as e:
        print(f"An error occurred while saving the file '{
              filepath}': {str(e)}")
        return False  # Return False if an error occurs
    return True  # Return True if the file was saved successfully


def convert_pdf2txt(src_dir, dest_dir):
    files = os.listdir(src_dir)
    files = [i for i in files if '.pdf' in i]
    for file in files:
        try:
            with pdfplumber.open(src_dir+file) as pdf:
                output = ''
                for page in pdf.pages:
                    output += page.extract_text()
                    output += '\n\nNEW PAGE\n\n'
                    print('Destination directory File Path:',
                          dest_dir+file.replace('.pdf', '.txt'))
                save_file(dest_dir+file.replace('.pdf', '.txt'),
                          output.strip())
        except Exception as oops:
            print("An error occurred:", oops, file)


def gpt_3(prompt):
    chatbot = open_file('pdfbot.txt')

    messages = [
        {"role": "system", "content": chatbot},
        {"role": "user", "content": prompt},
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.7,
        frequency_penalty=0,
        presence_penalty=0,
    )
    text = response['choices'][0]['message']['content']
    return text


# Create a Flask application instance
app = Flask(__name__)

# Define a route for the endpoint


@app.route('/pdfsummary', methods=['POST'])
def pdfsummary():
    try:
        # Load the OpenAI API key
        openai.api_key = os.getenv(
            'OPENAI_API_KEY') or open_file('openaiapikey.txt')

        print('Request received', request)

        # Get the PDF files from the request (use the key 'pdfs')
        pdf_files = request.files.getlist('pdfs')
        print("PDF files:", pdf_files)

        # Save the PDF files to a directory
        pdf_dir = 'PDFs/'
        for pdf_file in pdf_files:
            with open(os.path.join(pdf_dir, pdf_file.filename), 'wb') as f:
                f.write(pdf_file.read())

        # Convert PDFs to text
        convert_pdf2txt('PDFs/', 'textPDFs/')

        # Get a list of all text files in the specified folder
        pathfolder = 'textPDFs/'
        files = glob2.glob(pathfolder + '*.txt')
        print("Text files:", files)

        # Initialize an empty string to store the contents of all the text files
        alltext = ""

        # After converting PDFs to text and reading the text files
        for file in files:
            with open(file, 'r', encoding='utf-8') as infile:
                alltext += infile.read()

        # Print the content of alltext to check if it contains the expected text
        print("Extracted text from PDFs:", alltext)

        # Split the contents into chunks
        chunks = textwrap.wrap(alltext, 4000)

        # Before calling the GPT-3 model for summarization
        result = []
        for chunk in chunks:
            prompt = open_file('pdfprompt.txt').replace('<<SUMMARY>>', chunk)
            prompt = prompt.encode(encoding='ASCII', errors='ignore').decode()

            summary = gpt_3(prompt)
            result.append(summary)

            # Print the summary generated by the GPT-3 model
            print("Generated summary:", summary)

        summary_content = '\n\n'.join(result)

        chunks = textwrap.wrap(summary_content, 3000)

        # Write notes from chunks
        result = []  # Store notes
        result2 = []  # Store notes summaries
        for i, chunk in enumerate(chunks):
            with open("pdfprompt2.txt", 'r', encoding='utf-8') as infile:
                prompt = infile.read()
            prompt = prompt.replace("<<NOTES>>", chunk)
            notes = gpt_3(prompt)
            result.append(notes)

            keytw = open_file('pdfprompt3.txt').replace('<<NOTES>>', chunk)
            keytw2 = gpt_3(keytw)
            result2.append(keytw2)

        # Convert the lists to strings
        notes_string = "\n\n".join(result)
        study_guide_string = "\n\n".join(result2)

        # Use the summary of notes for further processing
        essential1 = open_file('pdfprompt4.txt').replace(
            '<<NOTES>>', study_guide_string)
        essential2 = gpt_3(essential1)

        result = {
            'summary': summary_content,
            'notes': notes_string,
            'notes_summary': study_guide_string,
            'essential_info': essential2
        }

        # Delete the uploaded PDF files and the converted .txt files
        for pdf_file in pdf_files:
            pdf_path = os.path.join(pdf_dir, pdf_file.filename)
            txt_path = os.path.join(
                pathfolder, pdf_file.filename.replace('.pdf', '.txt'))
            try:
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
                    print(f"Deleted PDF file: {pdf_path}")
                if os.path.exists(txt_path):
                    os.remove(txt_path)
                    print(f"Deleted TXT file: {txt_path}")
            except Exception as e:
                print(f"An error occurred while deleting files: {str(e)}")

        return jsonify(result), 200
    except Exception as e:
        print("An error occurred:", str(e))
        return jsonify({"error": str(e)}), 500


# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True, port=8000)
