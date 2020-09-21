import boto3
import time
from types import SimpleNamespace
from trp import Document
from PyPDF2 import PdfFileWriter, PdfFileReader
import io
from reportlab.pdfgen import canvas

class TextDetectionProcessor:
    def __init__(self, config):
        self.config = config

    def _start(self):
        response = None
        client = boto3.client('textract', self.config.awsRegion)
        response = client.start_document_text_detection(
            DocumentLocation={
                'S3Object': {
                    'Bucket': self.config.bucketName,
                    'Name': self.config.documentPath
                }
            },
        )

        return response['JobId']

    def _isComplete(self, jobId):
        time.sleep(10)
        client = boto3.client('textract', self.config.awsRegion)
        response = client.get_document_text_detection(JobId=jobId)
        status = response['JobStatus']
        print("Job Status: {}".format(status))

        while(status == 'IN_PROGRESS'):
            status = self._isComplete(jobId)

        return status

    def _getResults(self, jobId, pages):
        pageResults = pages
        client = boto3.client('textract', self.config.awsRegion)
        response = client.get_document_text_detection(JobId=jobId)
        pageResults.append(response)
        print("Resultset page recieved: {}".format(len(pages)))
        nextToken = None
        if('NextToken' in response):
            nextToken = response['NextToken']

        while(nextToken):
            self._getResults(jobId, pageResults)

        return pageResults

    def run(self):
        jobId = self._start()
        print("Started Asnyc Job with Id: {}".format(jobId))
        status = self._isComplete(jobId)
        if(status == "SUCCEEDED"):
            pages = self._getResults(jobId, [])
            return pages

jobConfig = SimpleNamespace(**{
    'awsRegion': 'us-east-2',
    'bucketName': 'phoenix-applicant-transcripts',
    'documentPath': 'American Public University sample 1.pdf'
})

outputDocument = PdfFileWriter()
baseDocument = PdfFileReader(open('American Public University sample 1.pdf', 'rb'))

processor = TextDetectionProcessor(jobConfig)
response = processor.run()

document = Document(response)

for index, pageBlock in enumerate(document.pageBlocks):
    existingPageSize = baseDocument.getPage(index).mediaBox
    existingPageHeight = existingPageSize.getHeight()
    existingPageWidth = existingPageSize.getWidth()

    byteStorage = io.BytesIO()

    overlay = canvas.Canvas(byteStorage, pagesize=(existingPageWidth, existingPageHeight), bottomup=0)
    overlay.setFont("Times-Roman", 8)

    for block in pageBlock['Blocks']:
        if('Confidence' in block and block['Confidence'] > 85 and block['BlockType'] == 'WORD'):
            textToDraw = block['Text']
            xPosition = block['Geometry']['BoundingBox']['Left'] * float(existingPageWidth)
            yPosition = block['Geometry']['BoundingBox']['Top'] * float(existingPageHeight)
            overlay.drawString(xPosition, yPosition, textToDraw)

    overlay.save()
    byteStorage.seek(0)
    overlayPdf = PdfFileReader(byteStorage)
    newDocumentPageX = overlayPdf.getPage(0)
    outputDocument.addPage(newDocumentPageX)


outputStream = open("ocrResult.pdf", "wb")
outputDocument.write(outputStream)
outputStream.close()