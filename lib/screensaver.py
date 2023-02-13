# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with Kodi; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html

## Screensaver that displays a slideshow of pictures grouped by the date the pictures were created.

#  This Program uses the database from the plugin.image.mypicsdb2 addon.
#  Pictures are selected from the database that were all taken on the 
#  same date.
#  A group of pictures from that date are displayed.
#  Another date is chosen, and another group of pictures are displayed, etc.

### Options for how the date is selected for each group of pictures:
 
#  1. A random date is chosen from the ImageDateTime field of all of the 
#     pictures. The same date is not chosen again until all dates have been used.
#  2. A filter that has been configured in the MyPicturesDatabase addon can be used.
#     The selected filter defines a subset of pictures from the MyPictures database.
#     A random date is chosen from the ImageDateTime field of the matching pictures. 
#     The first picture in the group will be a picture that matches the filter on
#     the chosen date. The rest of the pictures in the group will be those taken on
#     the same date. The additional pictures in the group may or may  not match the
#     filter. The same matching picture is not chosen until all matching pictures 
#     have been used. 


### Additional features:
 
#     1. Some information from each picture can be displayed by the screensaver.
#        - Image tags if they occur in the image file
#          - Headline
#          - Caption
#          - Sublocation, City, State/Province, Country
#        - The image date and time
#        - The image name
#     2. The current time can be displayed on each slide.
#     3. If pictures are taken in "burst mode" with a camera, then you may have
#        dozens of pictures, with multiple occuring in the same second, that look
#        almost identical. This makes for a very boring slideshow if each slide is 
#        shown for a few seconds. When there are many pictures taken very close 
#        together in time, the slideshow speeds up so that there is much less time 
#        between "burst mode" images.
#     4. If music is playing when the slideshow is running, information about the
#        currently playing music can be displayed.
#     5. Multiple slide transition effects can be chosen.
#     6. Slides can be displayed dimmed.

import os.path
import sys
import random
import time
import urllib.parse
from datetime import datetime

import xbmc
import xbmcgui
import xbmcaddon

import mypicsdb.MypicsDB  as MypicsDB

ADDON = xbmcaddon.Addon()

SETTINGS_ERROR = ADDON.getLocalizedString(30026)
NO_FILTER_NAME_ERROR = ADDON.getLocalizedString(30027)
BAD_FILTER_NAME_ERROR = ADDON.getLocalizedString(30028)
NO_FILES_MATCH_FILTER = ADDON.getLocalizedString(30029)

def log(msg, level=xbmc.LOGINFO):
        filename = os.path.basename(sys._getframe(1).f_code.co_filename)
        lineno  = str(sys._getframe(1).f_lineno)
        xbmc.log(str("[%s] line %5d in %s >> %s"%(ADDON.getAddonInfo('name'), int(lineno), filename, msg.__str__())), level)

# DateTimes are stored and retreived differently between mysql and sqlite.
IMGDATE =     {"mysql" :"DATE_FORMAT(ImageDateTime,'%Y-%m-%d')", 
               "sqlite":"SUBSTR(ImageDateTime, 0, 11)"}
IMGDATETIME = {"mysql" :"DATE_FORMAT(ImageDateTime,'%Y-%m-%d %T')", 
               "sqlite":"ImageDateTime"}

# Formats that can be displayed in a slideshow
PICTURE_FORMATS = ('bmp', 'jpeg', 'jpg', 'gif', 'png', 'tiff', 'mng', 'ico', 'pcx', 'tga')

# Random effect list for pan/zoom transitions
EFFECTLIST = ["('conditional', 'effect=zoom start=100 end=400 center=auto time=250000 condition=true'),",
              "('conditional', 'effect=slide start=1920,0 end=-1920,0 time=250000 condition=true'), ('conditional', 'effect=zoom start=%i end=%i center=auto time=250000 condition=true')",
              "('conditional', 'effect=slide start=-1920,0 end=1920,0 time=250000 condition=true'), ('conditional', 'effect=zoom start=%i end=%i center=auto time=250000 condition=true')",
              "('conditional', 'effect=slide start=0,1080 end=0,-1080 time=250000 condition=true'), ('conditional', 'effect=zoom start=%i end=%i center=auto time=250000 condition=true')",
              "('conditional', 'effect=slide start=0,-1080 end=0,1080 time=250000 condition=true'), ('conditional', 'effect=zoom start=%i end=%i center=auto time=250000 condition=true')",
              "('conditional', 'effect=slide start=1920,1080 end=-1920,-1080 time=250000 condition=true'), ('conditional', 'effect=zoom start=%i end=%i center=auto time=250000 condition=true')",
              "('conditional', 'effect=slide start=-1920,1080 end=1920,-1080 time=250000 condition=true'), ('conditional', 'effect=zoom start=%i end=%i center=auto time=250000 condition=true')",
              "('conditional', 'effect=slide start=1920,-1080 end=-1920,1080 time=250000 condition=true'), ('conditional', 'effect=zoom start=%i end=%i center=auto time=250000 condition=true')",
              "('conditional', 'effect=slide start=-1920,-1080 end=1920,1080 time=250000 condition=true'), ('conditional', 'effect=zoom start=%i end=%i center=auto time=250000 condition=true')"]
NO_EFFECT = []
CROSSFADE = 0
PANZOOM = 1
NONE = 2
FAST = 3
DISABLED = 0
FILENAME = 1
FOLDERNAME = 2
FOLDER_AND_FILENAME = 3
FULL_PATH = 4

# Get the Database from the My Pictures Database addon
MPDB = MypicsDB.MyPictureDB()

class Screensaver(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        pass

    def onInit(self):
        self.db_backend = xbmcaddon.Addon('plugin.image.mypicsdb2').getSetting('db_backend').lower()
        # Load variables
        self._get_vars()
        # Get addon settings
        self._get_settings()
        # Set UI Component information
        self._set_ui_components()
        # Initialize global lists 
        if self.slideshow_filter:
            # We are going to use a MyPicsDB filter, then get all of the possible pictures we could use to start a group
            self._get_filtered_pictures() # !SIDE EFFECT! Sets self.slideshow_filter to False on error
        if not self.slideshow_filter:
            # Not using a filter, so get a list of all the unique dates of the images
            self._get_unique_dates()
        # Start the show
        self._start_show()

    def _get_vars(self):
        # Get the screensaver window id
        self.winid = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        # Init the monitor class to catch onscreensaverdeactivated calls
        self.Monitor = MyMonitor(action = self._exit)
        self.stop = False
        # Set the skin name so we can have different looks for different skins
        self.winid.setProperty('SkinName',xbmc.getSkinDir())
        # Get MyPicsDB tagids for the information that can be displayed for each slide
        _query = " Select idTagType FROM TagTypes WHERE TagType = 'Headline'; "
        _ids = self._exec_query(_query)
        self.headline_tagid = _ids[0][0]
        _query = " Select idTagType FROM TagTypes WHERE TagType = 'Caption/abstract'; "
        _ids = self._exec_query(_query)
        self.caption_tagid = _ids[0][0]
        _query = " Select idTagType FROM TagTypes WHERE TagType = 'Sub-location'; "
        _ids = self._exec_query(_query)
        self.sublocation_tagid = _ids[0][0]
        _query = " Select idTagType FROM TagTypes WHERE TagType = 'City'; "
        _ids = self._exec_query(_query)
        self.city_tagid= _ids[0][0]
        _query = " Select idTagType FROM TagTypes WHERE TagType = 'Province/state'; "
        _ids = self._exec_query(_query)
        self.state_tagid= _ids[0][0]
        _query = " Select idTagType FROM TagTypes WHERE TagType = 'Country/primary location name'; "
        _ids = self._exec_query(_query)
        self.country_tagid= _ids[0][0]

    def _get_settings(self):
        # read addon settings
        self.anim_time = 101000
        self.slideshow_time = ADDON.getSettingInt('time')
        self.slideshow_limit = ADDON.getSettingInt('limit')
        self.slideshow_effect = ADDON.getSettingInt('effect')
        # convert float to hex value usable by the skin
        self.slideshow_dim = hex(int('%.0f' % (float(ADDON.getSettingInt('level')) * 2.55)))[2:] + 'ffffff'
        self.slideshow_bg = ADDON.getSettingBool('background')
        self.slideshow_scale = ADDON.getSettingBool('scale')
        self.slideshow_name = ADDON.getSettingInt('name')
        self.slideshow_date = ADDON.getSettingBool('date')
        self.slideshow_tags = ADDON.getSettingBool('tags')
        self.slideshow_music = ADDON.getSettingBool('music')
        self.slideshow_clock = ADDON.getSettingBool('clock')
        self.slideshow_filter = ADDON.getSettingBool('filter')
        self.slideshow_filtername = ADDON.getSettingString('filtername')
        self.slideshow_burst = ADDON.getSettingBool('burst')
        self.slideshow_burst_time = ADDON.getSettingInt('bursttime')
        # set the dim property
        self._set_prop('Dim', self.slideshow_dim)
        # show music info during slideshow if enabled
        if self.slideshow_music:
            self._set_prop('Music', 'show')
        # show background if enabled
        if self.slideshow_bg:
            self._set_prop('Background', 'show')
        # show clock if enabled
        if self.slideshow_clock:
            self._set_prop('Clock', 'show')

    def _set_ui_components(self):
        # select which image controls from the xml we are going to use
        if self.slideshow_scale:
            self.image1 = self.getControl(3)
            self.image2 = self.getControl(4)
            self.getControl(1).setVisible(False)
            self.getControl(2).setVisible(False)
            self.getControl(5).setVisible(False)
            self.getControl(6).setVisible(False)
        else:
            self.image1 = self.getControl(1)
            self.image2 = self.getControl(2)
            self.getControl(3).setVisible(False)
            self.getControl(4).setVisible(False)
            if self.slideshow_bg:
                self.image3 = self.getControl(5)
                self.image4 = self.getControl(6)
        
    def _get_filtered_pictures(self):
        # We are going to use a MyPicsDB filter, then get all of the possible pictures we could use to start a group
        if self.slideshow_filtername == "":
            # Use filter selected, but no filter name given
            message = 'Notification(' + SETTINGS_ERROR + ', ' + NO_FILTER_NAME_ERROR + ', 15000, DefaultIconError.png)'
            xbmc.executebuiltin(message)
            self.slideshow_filter = False
            log("Filter name was not specified",xbmc.LOGERROR)
        else:
            # Use filter selected, and filter name specified
            # Make sure the specified filter exists
            query = "Select pkFilter FROM FilterWizard"
            query += " WHERE strFilterName = '%s'; " %(self.slideshow_filtername.replace("'","''"))
            filter_ids = self._exec_query(query)
            if len(filter_ids) != 1:
                # Filter name was not found in the My Pictures Database.
                message = 'Notification(' + SETTINGS_ERROR + ', ' + BAD_FILTER_NAME_ERROR%(self.slideshow_filtername) + ', 15000, DefaultIconError.png)'
                xbmc.executebuiltin(message)
                self.slideshow_filter = False
                log("Filtername '%s' not found in MyPictures Database" %(self.slideshow_filtername), xbmc.LOGERROR)
            else:
                # Fliter name found, apply it to get the matching pictures.
                results = MPDB.filterwizard_get_pics_from_filter(self.slideshow_filtername, 0)
                # Make sure only displayable pictures are used
                filtered_results = [result for result in results if result[1].lower().endswith(PICTURE_FORMATS)]
                if len(filtered_results) == 0:
                    # No matching pictures found for the filter
                    message = 'Notification(' + SETTINGS_ERROR + ', ' + NO_FILES_MATCH_FILTER%(self.slideshow_filtername) + ', 15000, DefaultIconError.png)'
                    xbmc.executebuiltin(message)
                    self.slideshow_filter = False
                    log("No files match filter '%s'in MyPictures Database" %(self.slideshow_filtername), xbmc.LOGERROR)
                else:
                    # Need to get the idFile number and ImageDateTime for each of the matching images
                    self.completed_filtered_results = []
                    for (folder, file) in filtered_results:
                        query = \
                            " Select idFile, " + IMGDATETIME[self.db_backend]+ " FROM Files WHERE strPath = '%s' AND strFilename = '%s'; " \
                            %(folder.replace("'","''"), file.replace("'","''"))
                        file_info  = self._exec_query(query)
                        if len(file_info) > 0:
                            self.completed_filtered_results.append(file_info[0])
                    # Randomize the sequence of pictures that match the filter
                    random.shuffle(self.completed_filtered_results)
                    # At the start of the show, use the first random image idFile
                    self.filtered_results_index = 0

    def _get_unique_dates(self):
        # Not using a filter, so get a list of all the unique dates of the images
        query = " Select DISTINCT " + IMGDATE[self.db_backend] + " FROM Files WHERE ImageDateTime IS NOT NULL AND ImageDateTime != ''; "
        self.distinct_dates = self._exec_query(query)
        # Randomize the order that the date groups will be shown
        random.shuffle(self.distinct_dates)
        # At the start of the show, use the first random date
        self.results_index = 0

    def _start_show(self):
        # start with image 1
        current_image_control = self.image1
        order = [1,2]
        effect = self.slideshow_effect
        # loop until onScreensaverDeactivated is called
        while (not self.Monitor.abortRequested()) and (not self.stop):
            # Get the next grouping of pictures
            results = self._get_items()
            # First element of results is true if the pictures were taken in burst mode
            fastmode = results[0]
            # Second element of results is all of the pictures
            picture_group = results[1] # each element is [idFile, imgdatetime, strPath, strFilename]
            prev_effect = effect
            if fastmode:
                # Display this group of pictures quickly
                effect = FAST
                timetowait = 1000
                self._set_prop('Fade1', '0')
                self._set_prop('Fade2', '0')
                self._set_prop('NoEffectFade1', '0')
                self._set_prop('NoEffectFade2', '0')
                self.image1.setAnimations(NO_EFFECT)
                self.image2.setAnimations(NO_EFFECT)
                self.image1.setPosition(0,0)
                self.image2.setPosition(0,0)
                if self.slideshow_bg:
                    self.image3.setVisible(False)
                    self.image4.setVisible(False)
                    
                # Add picture information to slide for all images in burst mode
                self._set_prop('FadeinLabel', '0')
                self._set_prop('FadeoutLabel', '1')
                xbmc.sleep(1000)
                self._set_info_fields(picture_group[0])
                self._set_prop('FadeinLabel', '1')
                self._set_prop('FadeoutLabel', '0')
            else:
                timetowait = self.slideshow_time * 1000
                # Reset effect in case it was in burst mode
                effect = self.slideshow_effect
                if self.slideshow_bg:
                    self.image3.setVisible(True)
                    self.image4.setVisible(True)
            self._set_prop('Splash', 'hide')

            # iterate through all the images
            for picture in picture_group:
                            
                img_name = os.path.join(picture[2], picture[3])
                current_image_control.setImage(img_name, False)
                
                if not fastmode:
                    # add background image to gui
                    if (not self.slideshow_scale) and self.slideshow_bg:
                        if order[0] == 1:
                            self.image3.setImage(img_name, False)
                        else:
                            self.image4.setImage(img_name, False)

                    # Add picture information to slide
                    self._set_prop('FadeinLabel', '0')
                    self._set_prop('FadeoutLabel', '1')
                    xbmc.sleep(1000)
                    self._set_info_fields(picture)
                    self._set_prop('FadeinLabel', '1')
                    self._set_prop('FadeoutLabel', '0')

                    # set animations
                    if effect == CROSSFADE or effect == PANZOOM:
                        # add random slide/zoom anim
                        if effect == PANZOOM:
                            # add random slide/zoom anim
                            self._anim(current_image_control)
                        # add fade anim, used for both fade and slide/zoom anim
                        self._set_prop('Fade%d' % order[0], '0')
                        self._set_prop('Fade%d' % order[1], '1')
                    elif effect == NONE:
                        # we need to hide the images when no effect is selected, add fade effect with time=0
                        self._set_prop('NoEffectFade%d' % order[0], '0')
                        self._set_prop('NoEffectFade%d' % order[1], '1')
                    # add fade anim to background images
                    if self.slideshow_bg and effect != NONE:
                        self._set_prop('Fade1%d' % order[0], '0')
                        self._set_prop('Fade1%d' % order[1], '1')

                # define next image
                if current_image_control == self.image1:
                    current_image_control = self.image2
                    order = [2,1]
                else:
                    current_image_control = self.image1
                    order = [1,2]

                # display the image for the specified amount of time
                count = timetowait
                while (not self.Monitor.abortRequested()) and (not self.stop) and count > 0:
                    count -= 1000
                    if not fastmode:
                        xbmc.sleep(1000)
                    else:
                        xbmc.sleep(self.slideshow_burst_time)

                # break out of the for loop if onScreensaverDeactivated is called
                if  self.stop or self.Monitor.abortRequested():
                    break

    def _get_items(self, update=False):
        if self.slideshow_filter and self.slideshow_filtername != "":
            # Using a filter
            # Use the next picture that matched the filter, then get all of the pictures taken on the same date.
            # Set the offset into the list of pictures to be the picture that matched the filter.

            # Choose the date of one of the pictures that match the filter
            next_selected_result = self.completed_filtered_results[self.filtered_results_index]
            chosen_date = next_selected_result[1][0:10]
            # Next time choose the next matching picture
            self.filtered_results_index += 1
            if self.filtered_results_index == len(self.completed_filtered_results):
                # All of the pictures have been used, so start over with a new list of all of the pictures
                random.shuffle(self.completed_filtered_results)
                self.filtered_results_index = 0
            # Get the rest of the images that were taken on the chosen date
            query = " SELECT idFile, " + IMGDATETIME[self.db_backend] +", strPath, strFilename"
            query += " FROM Files "
            query += " WHERE " + IMGDATE[self.db_backend] + " = '%s' " %(chosen_date)
            query += " ORDER BY ImageDateTime, strFilename "
            results = self._exec_query(query)
            # Make sure only displayable pictures are used
            pictures_list = [result for result in results if result[3].lower().endswith(PICTURE_FORMATS)]
            # Find the offset in the list of pictures returned of the  picture that matched the query
            offset = 0;
            for picture in pictures_list:
                if picture[0] == next_selected_result[0]:
                    # file ids are the same
                    break
                offset += 1
        else:
            # Not using a filter
            # Use the next date in the list of unique dates, then get all of the pictures taken on the same date.
            # Set a random offset into the list of pictures so we don't always start wtih the earliest picture on the date.

            # Get some random date that at least one of the pictures was taken (each date is the single element of a list)
            chosen_date = self.distinct_dates[self.results_index][0]
            
            # Next time choose a new date
            self.results_index += 1
            if self.results_index == len(self.distinct_dates):
                # All of the dates have been used, so start over with a new list of all of the dates
                random.shuffle(self.distinct_dates)
                self.results_index = 0
            # Get the rest of the images that were taken on the chosen date
            query = "SELECT idFile, " + IMGDATETIME[self.db_backend] + ", strPath, strFilename "
            query += " FROM Files"
            query += " WHERE " + IMGDATE[self.db_backend] + " = '%s'" %(chosen_date)
            query += " ORDER BY ImageDateTime, strFilename"
            results = self._exec_query(query)
            # Make sure only diplayable pictures are used
            pictures_list = [result for result in results if result[3].lower().endswith(PICTURE_FORMATS)]
            # If there are more than 'limit' number of pictures in the list, 
            # Choose a random place to start in the ordered list of the pictures taken on the chosen date            
            if len(pictures_list) > self.slideshow_limit:
                offset = random.randrange(len(pictures_list) - self.slideshow_limit)
            else:
                offset = 0

        # We now have a list of pictures, and an offset into the list of the first picture to display
        if self.slideshow_burst:
            # Going to look for pictures taken in burst mode
            selected_picture = pictures_list[offset]
            # find all of the pictures after the selected one, where the time between pictures is no more than 2 seconds
            selected_image_datetime = selected_picture[1]
            previous_date_object = datetime.fromtimestamp(time.mktime(time.strptime(selected_image_datetime, '%Y-%m-%d %H:%M:%S')))
            picture_offset = offset + 1
            nearby_pictures_after = []
            while picture_offset < len(pictures_list):
                next_picture = pictures_list[picture_offset]
                this_image_datetime = next_picture[1]
                this_date_object = datetime.fromtimestamp(time.mktime(time.strptime(this_image_datetime, '%Y-%m-%d %H:%M:%S')))
                datediff = this_date_object - previous_date_object
                if datediff.total_seconds() <= 2:
                    nearby_pictures_after.append(pictures_list[picture_offset])
                    picture_offset += 1
                    previous_date_object = this_date_object
                else:
                    break
            # find all of the pictures before the selected one, where the time between pictures is no more than 2 seconds
            next_date_object = datetime.fromtimestamp(time.mktime(time.strptime(selected_image_datetime, '%Y-%m-%d %H:%M:%S')))
            picture_offset = offset - 1
            nearby_pictures_before = []
            while picture_offset >= 0:
                previous_picture = pictures_list[picture_offset]
                this_image_datetime = previous_picture[1]
                this_date_object = datetime.fromtimestamp(time.mktime(time.strptime(this_image_datetime, '%Y-%m-%d %H:%M:%S')))
                datediff = next_date_object - this_date_object
                if datediff.total_seconds() <= 2:
                    nearby_pictures_before.insert(0,pictures_list[picture_offset])
                    picture_offset -= 1
                    next_date_object = this_date_object
                else:
                    break
            picture_list = []
            if len(nearby_pictures_before) > 0 or len(nearby_pictures_after) > 0:
                # Pictures found that were taken no more than 2 seconds apart
                # Put all of them in the result
                picture_list.extend(nearby_pictures_before)
                picture_list.append(selected_picture)
                picture_list.extend(nearby_pictures_after)
                if len(picture_list) > 4:
                    result = (True,picture_list)
                else:
                    result = (False,pictures_list[offset:offset + self.slideshow_limit])
            else:
                # Did not find pictures in burst mode near selected picture
                result = (False,pictures_list[offset:offset + self.slideshow_limit])
        else:
            # Not checking for burst mode pictures    
            result = (False,pictures_list[offset:offset + self.slideshow_limit])
        return result

    def _set_info_fields(self, picture):
        self._clear_prop('Headline')
        self._clear_prop('Caption')
        self._clear_prop('Sublocation')
        self._clear_prop('City')
        self._clear_prop('State')
        self._clear_prop('Country')
        self._clear_prop('Date')
        self._clear_prop('Time')
        self._clear_prop('FolderLocation')
        self._clear_prop('Folder')
        self._clear_prop('File')
        self._clear_prop('FileExtension')
        # Get info to display in text fields
        if self.slideshow_tags:
            image_id=picture[0]
            # Get all of the tags that are on this image
            query = " Select idTagContent FROM TagsInFiles WHERE idFile = '%s'; " %(image_id)
            content_ids = self._exec_query(query)
            for content_id in content_ids:
                # Go through each of the tags, and store the ones of interest
                query = " Select idTagtype, TagContent FROM TagContents WHERE idTagContent = '%s'; " %(content_id[0])
                tags =  self._exec_query(query)
                tag_id = tags[0][0]
                tag_value = tags[0][1]
                if tag_id == self.headline_tagid:
                    self._set_prop('Headline',tag_value)
                elif tag_id == self.caption_tagid:
                    self._set_prop('Caption',tag_value)
                elif tag_id == self.sublocation_tagid:
                    self._set_prop('Sublocation',tag_value)
                elif tag_id == self.city_tagid:
                    self._set_prop('City',tag_value)
                elif tag_id == self.state_tagid:
                    self._set_prop('State',tag_value)
                elif tag_id == self.country_tagid:
                    self._set_prop('Country',tag_value)
        if self.slideshow_date:
            # Display the date the image was taken
            imgdatetime = picture[1]
            self._set_prop('Date',time.strftime('%A %B %e, %Y',time.strptime(imgdatetime, '%Y-%m-%d %H:%M:%S')))
            self._set_prop('Time',time.strftime('%I:%M:%S %p',time.strptime(imgdatetime, '%Y-%m-%d %H:%M:%S')))
        if self.slideshow_name != DISABLED:
            if self.slideshow_name == FILENAME:
                self._set_prop('File',os.path.splitext(picture[3])[0])
            elif self.slideshow_name == FOLDERNAME:
                self._set_prop('Folder',os.path.basename(picture[2]))
            elif self.slideshow_name == FOLDER_AND_FILENAME:
                self._set_prop('File',os.path.splitext(picture[3])[0])
                self._set_prop('Folder',os.path.basename(picture[2])+'/')
            elif self.slideshow_name == FULL_PATH:
                self._set_prop('File',os.path.splitext(picture[3])[0])
                self._set_prop('Folder',os.path.basename(picture[2])+'/')
                self._set_prop('FolderLocation',os.path.dirname(picture[2])+'/')
                self._set_prop('FileExtension',os.path.splitext(picture[3])[1])

    def _anim(self, current_image_control):
        # pick a random anim
        number = random.randint(0,8)
        posx = 0
        posy = 0
        # add 1 sec fadeout time to showtime
        anim_time = self.slideshow_time + 1
        # set zoom level depending on the anim time
        zoom = 110 + anim_time
        if number == 1 or number == 5 or number == 7:
            posx = int(-1920 + (19.2 * anim_time) + 0.5)
        elif number == 2 or number == 6 or number == 8:
            posx = int(1920 - (19.2 * anim_time) + 0.5)
        if number == 3 or number == 5 or number == 6:
            posy = int(-1080 + (10.8 * anim_time) + 0.5)
        elif number == 4 or number == 7 or number == 8:
            posy = int(1080 - (10.8 * anim_time) + 0.5)
        # position the current image
        current_image_control.setPosition(posx, posy)
        # add the animation to the current image
        if number == 0:
            current_image_control.setAnimations(eval(EFFECTLIST[number]))
        else:
            current_image_control.setAnimations(eval(EFFECTLIST[number] % (zoom, zoom)))

    # Utility functions
    def _exec_query(self,query):
        return MPDB.cur.request(query)

    def _set_prop(self, name, value):
        self.winid.setProperty('Screensaver.%s' % name, value)

    def _clear_prop(self, name):
        self.winid.clearProperty('Screensaver.%s' % name)

    def _exit(self):
        # exit when onScreensaverDeactivated gets called
        self.stop = True
        # clear our properties on exit
        self._clear_prop('Fade1')
        self._clear_prop('Fade2')
        self._clear_prop('Fade11')
        self._clear_prop('Fade12')
        self._clear_prop('Dim')
        self._clear_prop('Music')
        self._clear_prop('Clock')
        self._clear_prop('Splash')
        self._clear_prop('Background')
        self._clear_prop('Headline')
        self._clear_prop('Caption')
        self._clear_prop('Sublocation')
        self._clear_prop('City')
        self._clear_prop('State')
        self._clear_prop('Country')
        self._clear_prop('Date')
        self._clear_prop('Time')
        self._clear_prop('Folder')
        self._clear_prop('File')
        MPDB.cur.close()
        self.close()

# Notify when screensaver is to stop
class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        self.action = kwargs['action']

    def onScreensaverDeactivated(self):
        self.action()

    def onDPMSActivated(self):
        self.action()
