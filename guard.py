#!/usr/bin/python

import cv
import os
import logging as log
import Image

from datetime import datetime
from time import sleep

import argparse

import smtplib
from email import Encoders
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.Utils import formatdate

import motion

from settings import EMAIL_FROM, EMAIL_TO, EMAIL_SUBJECT, SENSITIVITY, STOP_ON_DETECT


COMMASPACE = ', '


class MotionAlert:
    capture = None
    image1 = None
    image2 = None
    diff = None
    email = None

    def __init__(self, cam=-1):
        self.capture = cv.CaptureFromCAM(cam)

    def capture_image(self, filename=None):
        for i in range(12):
            frame = cv.QueryFrame(self.capture)

        if not filename:
            filename = self.get_filename()

        try:
            os.unlink(filename)
        except OSError:
            log.warning('%s does not exists' % filename)

        cv.SaveImage(filename, frame)
        return filename

    def get_diff(self, delay=0.5):
        file1 = self.capture_image('1.jpg')
        sleep(delay)
        file2 = self.capture_image('2.jpg')
        
        self.image1 = Image.open(file1)
        self.image2 = Image.open(file2)

        self.diff = motion.images_diff(self.image1, self.image2)
        return self.diff

    def save_diff_images(self):
        if self.image1 and self.image2:
            canvas = Image.new('RGB', self.image1.size)
    
            key_image = motion.compare_images(self.image1, self.image2)
            finished_image = motion.green_key(canvas, key_image, self.image2)

            key_image.save(open(self.get_filename('green_key'), 'w'))
            finished_image.save(open(self.get_filename('finished_image'), 'w'))

        else:
            log.warning('No images captures')

    def send_email(self):
        HOST = "localhost"
 
        msg = MIMEMultipart()
        msg["From"] = EMAIL_FROM
        msg["To"] = COMMASPACE.join(EMAIL_TO)
        msg["Subject"] = EMAIL_SUBJECT
        msg['Date']    = formatdate(localtime=True)
 
        part = MIMEBase('application', "octet-stream")
        part.set_payload( open(self.image1.filename, "rb").read() )
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(self.image1.filename))
        msg.attach(part)
 
        server = smtplib.SMTP(HOST)
 
        try:
            failed = server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
            server.close()
        except Exception, e:
            error_msg = "Unable to send email. Error: %s" % str(e)
            log.warning(error_msg)

 
    def __exit__(self):
        del self.capture


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", help="Camera number")
    args = parser.parse_args()
    cam = int(args.camera) if args.camera else -1 
    m = MotionAlert(cam=cam)

    while True:
        diff = m.get_diff()
        if diff > SENSITIVITY:
            m.send_email()
            log.info('Email sent! (%s)' % diff)
            if STOP_ON_DETECT:
                break

