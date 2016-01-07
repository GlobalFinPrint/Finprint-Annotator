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
        self._min_area = 4000
        self.fgbg = cv2.createBackgroundSubtractorMOG2()

    def check_frame(self, frame):
        hits = []

        #apply backgroundsubtractor
        sub_frame = self.fgbg.apply(frame)

        # dilate the thresholded image to fill in holes, then find contours
        # on thresholded image
        thresh = cv2.dilate(sub_frame, None, iterations=2)
        (img, cnts, hierarchy) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        #
        # # loop over the contours
        for c in cnts:
            # if the contour is too small, ignore it
            ca = cv2.contourArea(c)
            if ca >= self._min_area:
                h = Hit()
                h.area = ca
                h.bounding_rectangle = cv2.boundingRect(c)
                hits.append(h)

        return hits
