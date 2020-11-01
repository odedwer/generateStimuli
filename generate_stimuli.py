###########################################################
######################### Imports #########################
###########################################################
import multiprocessing as mp
from random import randint

from PIL import Image, ImageOps, ImageDraw
import numpy as np
from tkinter import Tk
from tkinter.filedialog import askdirectory
import xlsxwriter as xl
from math import atan, pi, ceil, floor
from os import listdir, mkdir
from os.path import join as osp_join, curdir
from skimage.color import yiq2rgb, rgb2yiq

###########################################################
############# Parameters - don't change these #############
###########################################################

GRAYSCALE = 1

RGB = 0

NUM_OF_IMAGES_THAT_ARE_CONSIDERED_EDGE = 0  # 2

PARALLEL = False


def visual_deg_to_pix(deg, dist, physical_screen_size, resolution):
    """
    converts visual degrees to pixels
    :param deg: the visual degree
    :param dist: the distance from the screen
    :param physical_screen_size: the physical size of the screen
    :param resolution: the resolution of the screen
    :return: deg in relevant setup pixels
    """
    visual_angle_degrees = (2 * atan(physical_screen_size[0] / (2 * dist))) * (180 / pi)
    pixel_per_visual_angle = resolution[0] / visual_angle_degrees
    return round(deg * pixel_per_visual_angle)


###########################################################
####################### Parameters ########################
###########################################################

VIS_DEG_FOR_STIM = 3  # 1.25

BACKGROUND_IMAGE = 'background2_25_opacity.png'  # path to background image for cluttered background

LOCATION_PERMUTATION_FILE = r"LocationPerms.csv"  # path to a csv file containing the locations for the categories

NUM_OF_IMAGES_TO_CREATE_PER_CONDITION = 100

SCREEN_RESOLUTION = [1280, 1024]  # pixels, x,y - width, height

SCREEN_DISTANCE = 60  # cm

PHYSICAL_SCREEN_SIZE = [37.5, 30]  # x,y - width, height

TARGETS_EXPECTATION_PERCENTAGE = [1]  # [1, 1, 0.5]

TARGETS_REPETITION = False  # True allows for repetition of targets between different images

NUM_OF_TARGETS_PER_IMAGE = 1  # 2

DISTANCE_BETWEEN_IMAGES = [2]  # [0.9, 1.5, 0.9]  # percentage of image size between two images

RELEVANT_CATEGORY_INFO_NAME1 = 'sub_sub_category'  # this is the key in the info dict containing the
# category of the image which we want to split by
RELEVANT_CATEGORY_INFO_NAME2 = 'sub_category'  # in case 1 isn't available

ROI_COLOR = 'red'

ROI_LINE_WIDTH = 5

####################### automatically determined parameters ########################

TARGET_IMAGE_SIZE = [round(SCREEN_RESOLUTION[0] * 0.75), round(SCREEN_RESOLUTION[1] * 0.75)]

IMAGES_SIZE = visual_deg_to_pix(VIS_DEG_FOR_STIM, SCREEN_DISTANCE, PHYSICAL_SCREEN_SIZE, SCREEN_RESOLUTION)

# the amount of jitter to add to x,y location, relative to image size
LOCATION_JITTER = [int(ceil((IMAGES_SIZE * dist) / 10)) for dist in DISTANCE_BETWEEN_IMAGES]  # 4

IMAGES_ON_X = [TARGET_IMAGE_SIZE[0] // round(IMAGES_SIZE * dist) for dist in DISTANCE_BETWEEN_IMAGES]
print(f"IMAGES_ON_X: {IMAGES_ON_X}")
IMAGES_ON_Y = [TARGET_IMAGE_SIZE[1] // round((IMAGES_SIZE * dist)) for dist in DISTANCE_BETWEEN_IMAGES]
print(f"IMAGES_ON_Y: {IMAGES_ON_Y}")
ALL_IMAGES_NUM = [IMAGES_ON_X[i] * IMAGES_ON_Y[i] for i in range(len(IMAGES_ON_X))]

NUM_OF_NO_TARGET_IMAGES = [round((1 - expectancy) * NUM_OF_IMAGES_TO_CREATE_PER_CONDITION) for expectancy in
                           TARGETS_EXPECTATION_PERCENTAGE]
OVERALL_X_WIDTH = [IMAGES_SIZE * DISTANCE_BETWEEN_IMAGES[i] * IMAGES_ON_X[i] for i in range(len(IMAGES_ON_X))]
OVERALL_Y_HEIGHT = [IMAGES_SIZE * DISTANCE_BETWEEN_IMAGES[i] * IMAGES_ON_Y[i] for i in range(len(IMAGES_ON_Y))]
X_OFFSET = [((SCREEN_RESOLUTION[0] - x) // 2) - (IMAGES_SIZE // 2) for x in OVERALL_X_WIDTH]
Y_OFFSET = [((SCREEN_RESOLUTION[1] - y) // 2) - (IMAGES_SIZE // 2) for y in OVERALL_Y_HEIGHT]


# %%
###########################################################
####################### functions #########################
###########################################################

def _choose_image_directory():
    """
    GUI choice of directory
    :return: chosen directory path
    """
    root = Tk()
    root.withdraw()
    return askdirectory(title='Please choose image directory')


def _load_images(images_path):
    """
    loads images from chosen directory, separates them into targets and distractors
    :param images_path: path to image directory
    :return: list of: resized distractors list, target images list, original size targets lists
    """
    distractor_images_dict = dict()
    not_resized_targets = []
    targets = []
    categories_index = 1
    categories_dict = dict()
    image_names_list = [str(x) for x in listdir(images_path) if x[-3:] == "png"]
    for image_name in image_names_list:
        im = Image.open(osp_join(images_path, image_name)).convert('RGBA')
        _add_info_to_image(im, image_name)
        key = im.info[RELEVANT_CATEGORY_INFO_NAME2] + '_' + im.info[RELEVANT_CATEGORY_INFO_NAME1] \
            if RELEVANT_CATEGORY_INFO_NAME1 in im.info else im.info[RELEVANT_CATEGORY_INFO_NAME2]
        if key not in categories_dict:
            categories_dict[key] = categories_index
            categories_index += 1
        im.info["cat_num"] = categories_dict[key]
        if "target" in image_name:
            targets.append(im)
            not_resized_targets.append(im)
        else:
            if key in distractor_images_dict:
                distractor_images_dict[key].append(im)
            else:
                distractor_images_dict[key] = [im]
    # print("equalizing images...")
    # distractor_images_dict, targets = _equalize_images(distractor_images_dict, targets)
    print("resizing images...")
    _resize_images(distractor_images_dict, targets)
    print(categories_dict)
    return distractor_images_dict, targets, not_resized_targets, categories_dict


def _resize_images(distractor_images_dict, targets):
    """
    resizes the images
    :param distractor_images_dict: dictionary of lists of images
    :param targets: list of images
    """
    for key, lst in distractor_images_dict.items():
        _resize_image_list(lst)
    _resize_image_list(targets)


def _resize_image_list(lst):
    for i, im in enumerate(lst):
        w_percent = (IMAGES_SIZE / float(im.size[0]))
        h_size = int((float(im.size[1]) * float(w_percent)))
        im = im.resize((IMAGES_SIZE, h_size), Image.ANTIALIAS)
        lst[i] = im


def _add_info_to_image(im, image_name):
    """
    adds the information from the image name to the image info dictionary.
    change this function if the name convention has changed

    currently works on the following convention:
        category_subcategory_[subsubcategory_]number[_target].png
    :param im: the image
    :param image_name: the name of the image
    """
    im.info['filename'] = image_name
    im.info['target'] = True if "target" in image_name else False
    cat_end_index = image_name.find('_')
    im.info['category'] = image_name[:cat_end_index]
    sub_cat_end_index = cat_end_index + 1 + image_name[cat_end_index + 1:].find('_')
    im.info[RELEVANT_CATEGORY_INFO_NAME2] = image_name[cat_end_index + 1:sub_cat_end_index]
    if (image_name.count('_') > 2 and 'target' not in image_name) \
            or (image_name.count('_') > 3 and 'target' in image_name):
        sub_sub_cat_end_index = sub_cat_end_index + 1 + image_name[sub_cat_end_index + 1:].find('_')
        im.info[RELEVANT_CATEGORY_INFO_NAME1] = image_name[sub_cat_end_index + 1:sub_sub_cat_end_index]
    im.info["category_key"] = im.info[RELEVANT_CATEGORY_INFO_NAME2] + '_' + im.info[RELEVANT_CATEGORY_INFO_NAME1] \
        if RELEVANT_CATEGORY_INFO_NAME1 in im.info else im.info[RELEVANT_CATEGORY_INFO_NAME2]


def _make_output_folders():
    """
    create the output folders
    """
    failure = True
    try_idx = 1
    while failure:
        try:
            mkdir('generated_images' + str(try_idx))
            failure = False
            for i in range(len(TARGETS_EXPECTATION_PERCENTAGE)):
                cond_str = '_expectancy_' + str(TARGETS_EXPECTATION_PERCENTAGE[i]) + "_clutter_" + str(
                    DISTANCE_BETWEEN_IMAGES[i])
                mkdir(osp_join('generated_images' + str(try_idx), cond_str + '_Color'))
                mkdir(osp_join('generated_images' + str(try_idx), cond_str + '_Color_no_clutter'))
                mkdir(osp_join('generated_images' + str(try_idx), cond_str + '_BW'))
        except FileExistsError:
            try_idx += 1
    return try_idx


def _equalize_luminance(im, new_mean):
    im_arr = np.asarray(im)
    ret_im = np.zeros_like(im_arr, dtype=np.uint8)  # asarray is const
    ret_im[:, :, 3] = im_arr[:, :, 3]
    non_transparent_indices = (im_arr[:, :, 3] != 0)
    rgb = im_arr[:, :, 0:3] / 255  # turn to 0-1 image instead of 0-255
    yiq = rgb2yiq(rgb)
    cur_mean = np.mean(yiq[non_transparent_indices, 0])  # disregard pixels with alpha=0
    yiq[non_transparent_indices, 0] -= (cur_mean - new_mean)
    rgb = np.round(yiq2rgb(yiq) * 255)  # convert back to RGB nad non-normalized image
    rgb /= np.max(rgb)  # normalize
    rgb = np.round(rgb * 255)  # back to 0-255
    ret_im[:, :, 0:3] = rgb
    ret_im = Image.fromarray(ret_im)
    return ret_im


def _equalize_images(distractor_images_dict, targets):
    mean_lm_list = []
    # calculate mean luminance of each image
    # TODO: add contrast equalization
    for key in distractor_images_dict:
        for im in distractor_images_dict[key]:
            data = np.asarray(im)
            non_transparent_indices = (data[:, :, 3] != 0)
            yiq = rgb2yiq(data[:, :, 0:3] / 255)
            mean_lm_list.append(np.mean(yiq[non_transparent_indices, 0]))
    for im in targets:
        data = np.asarray(im)
        non_transparent_indices = (data[:, :, 3] != 0)
        yiq = rgb2yiq(data[:, :, 0:3] / 255)
        mean_lm_list.append(np.mean(yiq[non_transparent_indices, 0]))
    mean_lm = np.mean(mean_lm_list)
    for key in distractor_images_dict:
        for j in range(len(distractor_images_dict[key])):
            new_im = _equalize_luminance(distractor_images_dict[key][j], mean_lm)
            new_im.info = distractor_images_dict[key][j].info
            distractor_images_dict[key][j] = new_im
    for j in range(len(targets)):
        new_im = _equalize_luminance(targets[j], mean_lm)
        new_im.info = targets[j].info
        targets[j] = new_im
    return distractor_images_dict, targets


def _is_target(im):
    return im.info['target']


def _location_is_on_edge(location):
    """
    :param location: x,y coordinates
    :return: True if the location is considered to be an edge, False if not
    """
    return (location[0] > (TARGET_IMAGE_SIZE[0] - (NUM_OF_IMAGES_THAT_ARE_CONSIDERED_EDGE * IMAGES_SIZE)) or
            location[0] < NUM_OF_IMAGES_THAT_ARE_CONSIDERED_EDGE * IMAGES_SIZE or
            location[1] > (TARGET_IMAGE_SIZE[1] - (NUM_OF_IMAGES_THAT_ARE_CONSIDERED_EDGE * IMAGES_SIZE)) or
            location[1] < NUM_OF_IMAGES_THAT_ARE_CONSIDERED_EDGE * IMAGES_SIZE)


def _rotate_image(image, angle, representation):  # representation - RGB or GRAYSCALE
    image = ImageOps.expand(image, image.size * 2, (0, 0) if representation else (0, 0, 0, 0))
    image = image.rotate(angle)
    image = image.crop(image.getbbox())
    return image


def _get_locations(image_list, cond_index):
    """
    generates the list of location per image
    :param cond_index:
    :param image_list: the images to create locations for
    :return: a list of (x,y) coordinates for the images in the final image
    """
    # create grid coordinates jitters for each location
    jitters = np.random.randint(-LOCATION_JITTER[cond_index], LOCATION_JITTER[cond_index],
                                ALL_IMAGES_NUM[cond_index] * 2).reshape(
        (2, IMAGES_ON_Y[cond_index], IMAGES_ON_X[cond_index]))
    # create locations grid
    x, y = np.meshgrid(
        np.round(np.arange(IMAGES_ON_X[cond_index]) * (IMAGES_SIZE * DISTANCE_BETWEEN_IMAGES[cond_index])),
        np.round(np.arange(IMAGES_ON_Y[cond_index]) * (IMAGES_SIZE * DISTANCE_BETWEEN_IMAGES[cond_index])))

    # calculate offsets to x,y and center image locations
    x_offset = round(
        TARGET_IMAGE_SIZE[0] - (IMAGES_ON_X[cond_index] * IMAGES_SIZE * DISTANCE_BETWEEN_IMAGES[cond_index]))
    y_offset = round(
        TARGET_IMAGE_SIZE[1] - (IMAGES_ON_Y[cond_index] * IMAGES_SIZE * DISTANCE_BETWEEN_IMAGES[cond_index]))
    x += x_offset
    y += y_offset
    # add jitters
    x += jitters[0]
    y += jitters[1]
    # center the location, in case DISTANCE_BETWEEN_IMAGES is not 1
    x += int(IMAGES_SIZE - (IMAGES_SIZE * DISTANCE_BETWEEN_IMAGES[cond_index]))
    y += int(IMAGES_SIZE - (IMAGES_SIZE * DISTANCE_BETWEEN_IMAGES[cond_index]))
    # flatten for zip
    x = x.flatten() + X_OFFSET[cond_index]
    y = y.flatten() + Y_OFFSET[cond_index]
    x = x.astype(int)
    y = y.astype(int)
    image_locations = list(zip(x, y))
    target_positions = np.nonzero(list(map(_is_target, image_list)))[0]
    # move targets from edges
    for target_index in target_positions:
        cur_target_location = image_locations[target_index]
        new_loc_index = target_index
        while _location_is_on_edge(cur_target_location) or (
                new_loc_index in target_positions and new_loc_index != target_index):
            new_loc_index = randint(0, len(image_locations) - 1)
            cur_target_location = image_locations[new_loc_index]
        temp = image_locations[new_loc_index]
        image_locations[new_loc_index] = image_locations[target_index]
        image_locations[target_index] = temp
    return image_locations


def _paste_images(image_list, bw_image_list, locations, final_im, final_im_no_background, final_im_bw,
                  image_category_order):
    """
    rotates and pastes the images on the final images
    :param image_list: color images to paste (array shape n,1)
    :param bw_image_list: bw images to paste (array shape n,1)
    :param locations: locations of images for paste (top left corner of image, array shape n,2)
    :param final_im: color image to paste to
    :param final_im_no_background: color image with no background to paste to
    :param final_im_bw: bw image to paste to
    """
    used_indices = []
    image_list_sorted = []
    bw_image_list_sorted = []
    for cat_num in image_category_order:
        for i in range(len(image_list)):
            if image_list[i].info["cat_num"] == cat_num and i not in used_indices:
                image_list_sorted.append(image_list[i])
                bw_image_list_sorted.append(bw_image_list[i])
                used_indices.append(i)
                break
    target_indices = []
    angles = np.random.randint(-45, 45, len(locations))
    for i, loc in enumerate(locations):
        _rotate_and_paste_image(image_list_sorted[i], bw_image_list_sorted[i], loc, angles[i], final_im, final_im_bw,
                                final_im_no_background)
        if image_list_sorted[i].info['target']:
            target_indices.append(i)
    for i in target_indices:
        _rotate_and_paste_image(image_list_sorted[i], bw_image_list_sorted[i], locations[i], angles[i], final_im,
                                final_im_bw,
                                final_im_no_background)


def _rotate_and_paste_image(image, bw_image, loc, angle, final_im, final_im_bw, final_im_no_background):
    cur_img = _rotate_image(image, angle, RGB)
    cur_img_bw = _rotate_image(bw_image, angle, GRAYSCALE)
    final_im.paste(cur_img, loc, cur_img)
    final_im_no_background.paste(cur_img, loc, cur_img)
    final_im_bw.paste(cur_img_bw.convert('RGBA'), loc, cur_img_bw.convert('RGBA'))


def _create_locations_xl(locations_list, images, try_idx, image_num, categories_dict):
    doc = xl.Workbook(
        osp_join(curdir, "generated_images" + str(try_idx), 'target_locations' + str(image_num + 1) + '.xlsx'))
    sheet = doc.add_worksheet('target locations')
    sheet.write('A1', "Name")
    sheet.write('B1', "Target")
    sheet.write('C1', "Category")
    sheet.write('D1', "X")
    sheet.write('E1', "Y")
    for i, location in enumerate(locations_list):
        category = images[i].info[RELEVANT_CATEGORY_INFO_NAME2] + '_' + images[i].info[RELEVANT_CATEGORY_INFO_NAME1] \
            if RELEVANT_CATEGORY_INFO_NAME1 in images[i].info else images[i].info[RELEVANT_CATEGORY_INFO_NAME2]
        sheet.write('A' + str(i + 2), images[i].info['filename'])
        sheet.write('B' + str(i + 2), 1 if images[i].info['target'] else 0)
        sheet.write('C' + str(i + 2), category)
        sheet.write('D' + str(i + 2), location[0])
        sheet.write('E' + str(i + 2), location[1])
    doc.close()


def _save_images(final_image, final_image_bw, final_image_no_clutter, targets_im, targets_im_bw, image_num, try_idx):
    cond_index = image_num // NUM_OF_IMAGES_TO_CREATE_PER_CONDITION
    cond_str = '_expectancy_' + str(TARGETS_EXPECTATION_PERCENTAGE[cond_index]) + "_clutter_" + str(
        DISTANCE_BETWEEN_IMAGES[cond_index])
    color_dir_path = osp_join("generated_images" + str(try_idx), cond_str + "_Color")
    color_no_clutter_dir_path = osp_join("generated_images" + str(try_idx), cond_str + "_Color_no_clutter")
    bw_dir_path = osp_join("generated_images" + str(try_idx), cond_str + "_BW")
    final_image.convert('RGB').save(osp_join(curdir, color_dir_path, "image_" + str(image_num + 1) + ".png"), "PNG")
    final_image_no_clutter.convert('RGB').save(
        osp_join(curdir, color_no_clutter_dir_path, "image_" + str(image_num + 1) + ".png"), "PNG")
    final_image_bw.convert('LA').save(osp_join(curdir, bw_dir_path, "image_bw_" + str(image_num + 1) + ".png"))
    targets_im_bw.convert('LA').save(osp_join(curdir, bw_dir_path, "targets_bw_" + str(image_num + 1) + ".png"))
    targets_im.save(osp_join(curdir, color_dir_path, "targets_" + str(image_num + 1) + ".png"))
    targets_im.save(osp_join(curdir, color_no_clutter_dir_path, "targets_" + str(image_num + 1) + ".png"))


def _save_images_with_roi(final_images_with_roi, final_images_no_clutter_with_roi, final_images_bw_with_roi,
                          image_num, try_idx):
    cond_index = image_num // NUM_OF_IMAGES_TO_CREATE_PER_CONDITION
    cond_str = '_expectancy_' + str(TARGETS_EXPECTATION_PERCENTAGE[cond_index]) + "_clutter_" + str(
        DISTANCE_BETWEEN_IMAGES[cond_index])
    color_dir_path = osp_join("generated_images" + str(try_idx), cond_str + "_Color")
    color_no_clutter_dir_path = osp_join("generated_images" + str(try_idx), cond_str + "_Color_no_clutter")
    bw_dir_path = osp_join("generated_images" + str(try_idx), cond_str + "_BW")
    for i, image in enumerate(final_images_with_roi):
        image.convert('RGB').save(
            osp_join(curdir, color_dir_path, "image_" + str(image_num + 1) + "_with_roi_" + str(i + 1) + ".png"), "PNG")
    for i, image in enumerate(final_images_no_clutter_with_roi):
        image.convert('RGB').save(osp_join(curdir, color_no_clutter_dir_path,
                                           "image_" + str(image_num + 1) + "_no_clutter_with_roi_" +
                                           str(i + 1) + ".png"), "PNG")
    for i, image in enumerate(final_images_bw_with_roi):
        image.convert('RGB').save(
            osp_join(curdir, bw_dir_path, "image_bw_" + str(image_num + 1) + "_with_roi_" + str(i + 1) + ".png"), "PNG")


def _generate_roi(final_images_list, location_list, color=ROI_COLOR, width=ROI_LINE_WIDTH):
    """
    draws an ROI red square in the given
    :param final_images_list:
    :param location_list:
    :return:
    """
    ret_list = []
    for im in final_images_list:
        im_rois = []
        for i in range(NUM_OF_TARGETS_PER_IMAGE):
            if not location_list:
                im_rois.append(im.copy())
            else:
                loc = location_list[i]
                im_c = im.copy()
                draw = ImageDraw.Draw(im_c)
                draw.rectangle(
                    [loc[0] - floor(0.2 * IMAGES_SIZE),
                     loc[1] - floor(0.2 * IMAGES_SIZE),
                     loc[0] + floor(1.2 * IMAGES_SIZE),
                     loc[1] + floor(1.2 * IMAGES_SIZE)], outline=color)  # width=width
                im_rois.append(im_c)
        ret_list.append(im_rois)
    return ret_list


def _generate_targets_images(targets):
    """
    creates image of targets side by side
    :param targets: the targets to create the image from
    """
    targets_im_x_size, targets_im_y_size = sum(target.size[0] for target in targets), max(
        target.size[1] for target in targets)
    targets_im = Image.new('RGBA', (targets_im_x_size, targets_im_y_size), color="gray")
    targets_im_bw = Image.new('LA', (targets_im_x_size, targets_im_y_size), color="gray")
    x_offset = 0
    for target in targets:
        targets_im.paste(target, (x_offset, 0))
        targets_im_bw.paste(target.convert('L'), (x_offset, 0))
        x_offset += target.size[0]
    return targets_im, targets_im_bw


def _choose_targets(targets, not_resized_targets):
    """
    chooses the targets for the different images
    :param targets: list of target images
    :param not_resized_targets: list of target images, original size
    :return: list of lists of chosen targets, list of lists of chosen targets on original size
    """
    chosen_targets, not_resized_chosen_targets = [], []
    chosen_indices = np.random.choice(np.arange(len(targets)), NUM_OF_IMAGES_TO_CREATE_PER_CONDITION * len(
        TARGETS_EXPECTATION_PERCENTAGE) * NUM_OF_TARGETS_PER_IMAGE,
                                      TARGETS_REPETITION)
    targets_pairings = [chosen_indices[i::NUM_OF_TARGETS_PER_IMAGE] for i in range(NUM_OF_TARGETS_PER_IMAGE)]
    chosen_indices = list(zip(*targets_pairings))
    for tup in chosen_indices:
        chosen_targets.append([])
        not_resized_chosen_targets.append([])
        for index in tup:
            chosen_targets[-1].append(targets[index])
            not_resized_chosen_targets[-1].append(not_resized_targets[index])
    return chosen_targets, not_resized_chosen_targets


def _choose_image_lists(chosen_targets, distractor_images_dict):
    """

    :param chosen_targets:
    :param distractor_images_dict:
    :return:
    """

    num_of_categories = len(distractor_images_dict)
    num_of_images_per_category = [ceil(image_num / num_of_categories) for image_num in ALL_IMAGES_NUM]
    print(f"number of images per category: {num_of_images_per_category}")
    images_list = []
    for i, targets in enumerate(chosen_targets):  # go through all target images of each image to create
        cond_index = i // NUM_OF_IMAGES_TO_CREATE_PER_CONDITION  # every NUM_OF_IMAGES_TO_CREATE_PER_CONDITION
        # is a new condition
        chosen_targets_categories = dict()
        add_targets = (i % NUM_OF_IMAGES_TO_CREATE_PER_CONDITION) >= NUM_OF_NO_TARGET_IMAGES[cond_index]
        if add_targets:
            for target in targets:  # count how many targets are from each category
                key = target.info["category_key"]
                if key in chosen_targets_categories:
                    chosen_targets_categories[key] += 1
                else:
                    chosen_targets_categories[key] = 1
        cur_image_list = []
        for category in distractor_images_dict:  # choose and add distractors
            a = np.array(distractor_images_dict[category], dtype=Image.Image)
            size = num_of_images_per_category[cond_index] - (0 if category not in chosen_targets_categories else
                                                             chosen_targets_categories[category])
            cur_image_list += list(np.random.choice(a, size=size, replace=True if size > len(a) else False))
        if add_targets:
            for target in targets:  # join the targets and distractors
                cur_image_list.append(target)
        images_list.append(cur_image_list)
    return images_list


def generate_image(args):
    """
    main function. all changes should be done here only
    """
    try_idx, image_num_entry, image_list, not_resized_targets, categories_dict, image_category_order = args

    bw_image_list = [im.convert('LA') for im in image_list]

    # get locations of images on final image
    locations = _get_locations(image_list, image_num_entry // NUM_OF_IMAGES_TO_CREATE_PER_CONDITION)

    # create final images
    final_im_bw = Image.new('RGBA', TARGET_IMAGE_SIZE, color="gray")
    final_im = Image.open(BACKGROUND_IMAGE).convert('RGBA').resize(TARGET_IMAGE_SIZE, Image.ANTIALIAS)
    final_im_no_background = Image.new('RGBA', TARGET_IMAGE_SIZE, color="gray")

    # paste images to final images
    _paste_images(image_list, bw_image_list, locations, final_im, final_im_no_background, final_im_bw,
                  image_category_order)

    targets_im, targets_im_bw = _generate_targets_images(not_resized_targets)

    _save_images(final_im, final_im_bw, final_im_no_background, targets_im, targets_im_bw, image_num_entry, try_idx)

    _create_locations_xl(locations, image_list, try_idx, image_num_entry, categories_dict)
    # create ROI's
    target_locations = [loc for i, loc in enumerate(locations) if image_list[i].info['target']]
    final_image_with_roi, final_image_no_clutter_with_roi, final_image_bw_with_roi = _generate_roi(
        [final_im, final_im_no_background, final_im_bw], target_locations)
    _save_images_with_roi(final_image_with_roi, final_image_no_clutter_with_roi, final_image_bw_with_roi,
                          image_num_entry, try_idx)
    print("image %s saved." % image_num_entry)


def main():
    print("loading images...")
    distractor_images_dict, targets, not_resized_targets, categories_dict = _load_images(_choose_image_directory())
    # print("equalizing images...")
    # distractor_images_dict, targets = equalize_images(distractor_images_dict, targets)
    print("creating output folder...", end=" ")
    try_idx = _make_output_folders()
    print("Files will be saved under generated_images%s folder" % try_idx)
    print("choosing targets...")
    chosen_targets, not_resized_chosen_targets = _choose_targets(targets, not_resized_targets)
    print("choosing image lists...")
    image_lists = _choose_image_lists(chosen_targets, distractor_images_dict)
    perms = np.genfromtxt('LocationPerms.csv', delimiter=',')
    if PARALLEL:
        pool = mp.Pool()
        print("starting parallel generation of images...")
        pool.map(generate_image,
                 [(try_idx, num, image_lists[num], not_resized_chosen_targets[num], categories_dict, perms[num, :]) for
                  num in
                  range(NUM_OF_IMAGES_TO_CREATE_PER_CONDITION * len(TARGETS_EXPECTATION_PERCENTAGE))])
    else:
        print("starting generation of images...")
        for num in range(NUM_OF_IMAGES_TO_CREATE_PER_CONDITION * len(TARGETS_EXPECTATION_PERCENTAGE)):
            generate_image(
                args=(try_idx, num, image_lists[num], not_resized_chosen_targets[num], categories_dict, perms[num, :]))


if __name__ == "__main__":
    main()
