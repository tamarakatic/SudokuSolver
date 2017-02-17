import cv2
import numpy as np
import glob
import os.path
from sklearn.neighbors import KNeighborsClassifier
from sklearn.datasets import fetch_mldata

from sudoku_solver import sudoku

def train_knn_mnist():
    dataset = fetch_mldata('MNIST original')
    model = KNeighborsClassifier(n_neighbors=1)
    model.fit(dataset.data, dataset.target)
    return model

def import_image(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    blur = cv2.medianBlur(gray.copy(), 5)
    thresh = cv2.adaptiveThreshold(blur,255,1,1,11,2)

    return img, thresh

def crop_image(thresh):
    _, contours, _ = cv2.findContours(thresh.copy(),
                                      cv2.RETR_EXTERNAL,
                                      cv2.CHAIN_APPROX_SIMPLE)

    max_area = 0
    mask = None
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > max_area:
            max_area = area
            mask = cnt

    bounding_rect = cv2.boundingRect(mask)
    x, y, w, h = bounding_rect
    oppening = np.zeros((h, w), np.float)
    oppening[0:h, 0:w] = thresh[y:y + h, x:x + w]

    return oppening, bounding_rect

def filter_image(oppening, bounding_rect):
    kernel = np.zeros((11,11),dtype=np.uint8)
    kernel[5,...] = 1
    line = cv2.morphologyEx(oppening,cv2.MORPH_OPEN, kernel, iterations=2)
    oppening-=line

    x, y, w, h = bounding_rect
    oppening_cann = np.empty((h, w), np.uint8)
    oppening_cann[:, :] = oppening[:, :]

    #cv2.imshow('Lines morphologyEx', oppening)

    lines = cv2.HoughLinesP(oppening_cann, 1, np.pi/180, 106, 80, 10)
    for line in lines:
        for x1,y1,x2,y2 in line:
            cv2.line(oppening,(x1,y1),(x2,y2),(0,0,0), 3)

    #cv2.imshow('Hough Lines', oppening)

    #oppening = cv2.dilate(oppening, (10, 10), iterations = 1)

    #cv2.imshow('Dilate', oppening)
    return oppening, bounding_rect

def create_dataset(img_url):
    training_img = []
    training_label = []
    for img in glob.glob(img_url):
        image = cv2.imread(img)
        gray = 255 - cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, 0)

        _, contours, _ = cv2.findContours(thresh.copy(),
                                          cv2.RETR_EXTERNAL,
                                          cv2.CHAIN_APPROX_SIMPLE)

        rectangles = []
        for cnt in contours:
            rectangles.append(cnt)

        numbers = []
        for num in rectangles:
            x, y, w, h = cv2.boundingRect(num)
            number = np.zeros((h,w), np.uint8)
            number[:h, :w] = thresh[y:y + h, x:x + w]
            number = img_resize(number, 28, 28)
            flat = number.reshape(-1, 28*28).astype(np.float32)
            training_img.append(flat)

            training_label.append(int(os.path.basename(img)[0]))

    training_label = np.array(training_label).reshape(len(training_label), 1)
    training_img = np.array(training_img).reshape(len(training_img), -1)

    return training_img, training_label

def train_knn(samples, labels):
    model = cv2.ml.KNearest_create()
    model.train(samples, cv2.ml.ROW_SAMPLE, labels)
    return model

def predict(test_img, model):
    resize_img = test_img.reshape(-1, 28*28).astype(np.float32)
    returnVel, result, neighbors, dist = model.findNearest(resize_img, k=3)
    return result[0][0]

def find_numbers(oppening, gray, rectangles_img):
    _, num_contours, _ = cv2.findContours(oppening.astype("uint8").copy(),
                                      cv2.RETR_EXTERNAL,
                                      cv2.CHAIN_APPROX_SIMPLE)

    num_rectangle = []
    bounding_rectangles = []
    for num_contour in num_contours:
        x, y, w, h = cv2.boundingRect(num_contour)
        if w > 7 and h > 10 and h < 42:
            bounding_rectangles.append((x, y, w, h))
            num_rectangle.append(num_contour)

    numbers = []
    for number in num_rectangle:
        x, y, w, h = cv2.boundingRect(number)
        cv2.rectangle(rectangles_img, (x - 4,y - 4), (x + w + 3, y + h + 4), (0, 255, 0), 2)
        number = np.zeros((h,w), np.uint8)
        number[:h, :w] = gray[y:y + h, x:x + w]
        number = img_resize(number, 28, 28)
        numbers.append(number)

    ret = [(numbers[i], bounding_rectangles[i]) for i in range(len(numbers))]

    return ret

def img_resize(image, height, width):
    shape = (height,width)
    h, w = image.shape
    w = width if w > width else w
    h = height if h > height else h

    x_offset = abs(width - w)
    y_offset = abs(height - h)

    frame = np.zeros((height,width), np.uint8)

    x_start = x_offset / 2 if x_offset != 0 else 0
    y_start = y_offset / 2 if y_offset != 0 else 0

    frame[y_start:h + y_start, x_start:w + x_start] = image[0:h, 0:w]

    return frame

def show_image(img, name, contours):
    for cont in contours:
        x, y, w, h = cv2.boundingRect(cont)
        if w > 38 and w < 60 and h > 40 and h < 50:
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2)

    cv2.drawContours(img, contours, -1, (0, 255, 0), 3)
    cv2.imshow(name, img)

def intersection_area(boxA, boxB):
    left = max(boxA[0], boxB[0])
    top = max(boxA[1], boxB[1])
    right = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
    bottom = min(boxA[1] + boxA[3], boxB[1] + boxB[3])

    if left <= right and top <= bottom:
        return abs((right - left) * (bottom - top))

    return -1

img, thresh = import_image('sudoku_images/image7.jpg')
crop, rectangle = crop_image(thresh)

pers_crop = crop.copy()

x, y, w, h = rectangle

orig_cropped = np.zeros((h, w, 3), np.uint8)
orig_cropped[:h, :w, :] = img[y:y+h, x:x+w, :]
find_crop = orig_cropped.copy()

gray_test = 255 - cv2.cvtColor(find_crop, cv2.COLOR_BGR2GRAY)
gray_test_origin = gray_test.copy()

blur_test = cv2.GaussianBlur(gray_test,(5,5),0)
thresh_test = cv2.adaptiveThreshold(blur_test, 255, 1, 1, 11, 2)

_, contours, _ = cv2.findContours(thresh_test.copy(),
                                  cv2.RETR_EXTERNAL,
                                  cv2.CHAIN_APPROX_SIMPLE)

result = {}
areas = []
for cnt in contours:
    num_test = cnt.copy()
    cx, cy, cw, ch = cv2.boundingRect(num_test)
    if cw > 30 and cw < 70 and ch > 30 and ch < 60:
        areas.append((cx, cy, cw, ch))

sort_y = sorted(areas, key=lambda r: r[1])

rows = []
for i in range(9):
    sliced_row = sort_y[i * 9:(i + 1) * 9]
    sorted_y = sorted(sliced_row, key=lambda r: r[0])
    rows.append(sorted_y)


filt_img, rect = filter_image(crop, rectangle)
numbers = find_numbers(filt_img, crop, orig_cropped)
# cv2.waitKey()

samples, labels = create_dataset('dataset/*.jpg')
model = train_knn(samples, labels)

intersections = {}

for i in range(9):
    for j in range(9):
        for idx, (number_image, num_rectangle) in enumerate(numbers):
            area = intersection_area(num_rectangle, rows[i][j])

            if not idx in intersections:
                intersections[idx] = 0

            if area > 0 and area > intersections[idx]:
                intersections[idx] = (i, j)

sudoku_table = np.zeros((9, 9), np.uint8)

for number_index, (row, column) in intersections.iteritems():
    recognized_number = predict(numbers[number_index][0], model)
    sudoku_table[row, column] = recognized_number

success, steps = sudoku(sudoku_table)

print sudoku_table

cv2.imshow('Number', orig_cropped)
cv2.waitKey(0)