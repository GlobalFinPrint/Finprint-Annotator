import argparse
import imutils
import time
import cv2


class Hit(object):
    def __init__(self):
        self.area = None
        self.bounding_rectangle = None
        self.position = None


class ElasmoFinder(object):
    def __init__(self):
        self._capture = None
        self._min_area = 4000
        self.hits = []

    def process_video(self, file_name):
        self._capture = cv2.VideoCapture(file_name)
        self._capture.set(cv2.CAP_PROP_FPS, 120)
        fgbg = cv2.createBackgroundSubtractorMOG2()

        # loop over the frames of the video
        while True:
            (grabbed, frame) = self._capture.read()

            # if the frame could not be grabbed, then we have reached the end
            # of the video
            if not grabbed:
                break

            frame = imutils.resize(frame, width=900)

            #apply backgroundsubtractor
            sub_frame = fgbg.apply(frame)

            # dilate the thresholded image to fill in holes, then find contours
            # on thresholded image
            thresh = cv2.dilate(sub_frame, None, iterations=2)
            (img, cnts, hierarchy) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            #
            # # loop over the contours
            for c in cnts:
                # if the contour is too small, ignore it
                ca = cv2.contourArea(c)
                if ca < self._min_area:
                    continue

                h = Hit()
                h.area = ca
                h.bounding_rectangle = cv2.boundingRect(c)
                h.position = self._capture.get(cv2.CAP_PROP_POS_MSEC)
                self.hits.append(h)

        # cleanup the camera and close any open windows
        self._capture.release()
