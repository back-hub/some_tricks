import urllib

import fitz
import uuid
import tempfile

import xmltodict
from pyzbar.pyzbar import decode
from PIL import Image
import os
import base64
import zipfile


class PdfParse():
    def __init__(self,link):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfile = str(uuid.uuid4()) + ".pdf"
            self._download_pdf(link,tmpdir+tmpfile)
            self.pdf_file = fitz.open(tmpdir+tmpfile)
            self.pngs = []
            self.qrinfo = []
            self.base64_ordered = {}
            self.byte_list = []

    def _download_pdf(self, link, name):
        urllib.request.urlretrieve(link, name)

    def _extract_images(self, directory):
        # Iterating over each page in pdf
        for current_page_index in range(len(self.pdf_file)):
            # Iterating over each image on each PDF page and write it to temporary directory with random uuid name
            for img_index, img in enumerate(self.pdf_file.getPageImageList(current_page_index)):
                random_name = str(uuid.uuid4()) + ".png"
                xref = img[0]
                image = fitz.Pixmap(self.pdf_file, xref)
                image.writePNG(f"{directory}/{random_name}")
                self.pngs.append(random_name)

    def _image_resize(self, directory):
        self._extract_images(directory)
        # Changing size of png file (make it bigger)
        for filename in self.pngs:
            path_to_images = f"{directory}/{filename}"
            im = Image.open(f"{directory}/{filename}")
            resized = im.resize((400, 400))
            resized.save(f"{directory}/{filename}")

    def scan_qr(self, directory):
        self._image_resize(directory)
        # Reading QR-code and save decoded data in list xml_list
        for i in self.pngs:
            try:
                img_qrcode = Image.open(f"{directory}/{i}")
                decoded = decode(img_qrcode)
                xml_info = decoded[0].data.decode("utf-8")
                if "<?xml" in xml_info:
                    self.qrinfo.append(xmltodict.parse(xml_info))
            except Exception as e:
                print("Image isn't QR-code or QR-code isn't detected:" + str(e))

    def get_total_parts(self):
        return dict(self.qrinfo[0])['BarcodeElement']["elementsAmount"]

    def _get_xml_from_qr(self):
        for i in self.qrinfo:
            tmp = dict(i)
            self.base64_ordered[tmp['BarcodeElement']['elementNumber']] = tmp['BarcodeElement']['elementData']

    def get_bytes_from_xml(self):
        self._get_xml_from_qr()
        for i in range(1, int(self.get_total_parts()) + 1):
            self.byte_list.append(base64.b64decode(self.base64_ordered[str(i)]))

    def write_bytes(self, directory):
        bytes_length = 0
        zipfilename = f"{directory}/zipname.zip"
        with open(zipfilename, "wb") as f:
            for el in self.byte_list:
                f.write(el)
                bytes_length = bytes_length + len(el)
                f.seek(bytes_length)

    def _unzipfile(self, directory):
        file_zip = zipfile. ZipFile(f"{directory}/zipname.zip")
        file_zip.extractall(directory)
        return os.listdir(directory)

    def extract_fin_xml(self, directory):
        files = self._unzipfile(directory)
        results_xml = []
        for file in files:
            if file == "zipname.zip":
                continue
            with open(f"{directory}/{file}", "r") as f:
                results_xml.append(''.join(f.readlines()))
        return results_xml


    def parse(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.scan_qr(tmpdir)
        self.get_bytes_from_xml()
        with tempfile.TemporaryDirectory() as tmpdir:
            self.write_bytes(tmpdir)
            return self.extract_fin_xml(tmpdir)


class BaseFilter():
    def __init__(self, link):
        self.xml_str = PdfParse(link).parse()
        self._check()
        self.raw_data=xmltodict.parse(self.xml_str[0])

    def _check(self):
        if len(self.xml_str) != 1:
            raise Exception("xml parse error: too many xmls")
