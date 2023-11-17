from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File
from pdfplumber import open as pdf_open
from pymongo import MongoClient
from dotenv import load_dotenv
from bson import ObjectId
import spacy
import os

load_dotenv()
client = MongoClient(os.getenv('CONNECT_STRING'))
db = client['docinfo']
collection = db['docinfo']
app = FastAPI()
nlp = spacy.load('en_core_web_sm')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)


def extract_information(pdf_path):
    information = {
        'Reference': '',
        'Date': '',
        'Subject': '',
        'Reason': '',
        'Sender': '',
        'Receiver': ''
    }

    with pdf_open(pdf_path) as pdf:
        full_text = ''
        for page in pdf.pages:
            text = page.extract_text()
            full_text += text

        doc = nlp(full_text)

        for ent in doc.ents:
            if ent.label_ == 'DATE':
                information['Date'] = ent.text
            elif ent.label_ == 'PERSON':
                if not information['Sender']:
                    information['Sender'] = ent.text
                else:
                    information['Receiver'] = ent.text
            elif ent.label_ == 'ORG':
                information['Receiver'] = ent.text
            elif 'Reference' in ent.text:
                information['Reference'] = ent.text.split(
                    'Reference')[-1].strip()
            elif 'Subject' in ent.text:
                information['Subject'] = ent.text.split('Subject')[-1].strip()
            elif 'Reason' in ent.text:
                information['Reason'] = ent.text.split('Reason')[-1].strip()

    return information


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    if file.filename.endswith('.pdf'):
        file_contents = await file.read()
        with open(file.filename, 'wb') as f:
            f.write(file_contents)

        pdf_information = extract_information(file.filename)

        return pdf_information
    else:
        return {"error": "Please upload a PDF file."}


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/uploadinfo")
async def upload_info(info: dict):
    xx = collection.insert_one(info)
    return {"id": str(xx.inserted_id)}


@app.get("/getinfo")
async def get_info(id: str):
    allel = collection.find_one({"_id": ObjectId(str(id))})
    allel.pop('_id')
    return str(allel)
