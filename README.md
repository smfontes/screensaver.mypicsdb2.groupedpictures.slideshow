# screensaver.mypicsdb2.groupedpictures.slideshow

## Screensaver that displays a slideshow of pictures grouped by the date the pictures were created.

 This Screensaver has only been tested with Kodi version 19.4 and with plugin.image.mypicsdb2 version 19.4.4. 

 This Screensaver uses the database from the plugin.image.mypicsdb2 addon.
 Pictures are selected from the database that were all taken on the same date.
 A group of pictures from that date are displayed.
 Another date is chosen, and another group of pictures are displayed, etc.

### Options for how the date is selected for each group of pictures:
 
   1. A random date is chosen from the ImageDateTime field of all of the pictures. The same date is not chosen again until all dates have been used.
   2. A filter that has been configured in the MyPicturesDatabase addon can be used. The selected filter defines a subset of pictures from the MyPictures database. A random date is chosen from the ImageDateTime field of the matching pictures. The same matching picture is not chosen until all matching pictures have been used.


### Additional features:
 
    1. Some information from each picture can be displayed by the screensaver.
       - Image tags if they occur in the image file
         - Headline
         - Caption
         - Sublocation, City, State/Province, Country
       - The image date and time
       - The image name
    2. The current time can be displayed on each slide.
    3. If pictures are taken in "burst mode" with a camera, then you may have
       dozens of pictures, with multiple occuring in the same second, that look
       almost identical. This makes for a very boring slideshow if each slide is 
       shown for a few seconds. When there are many pictures taken very close 
       together in time, the slideshow speeds up so that there is much less time 
       between "burst mode" images.
    4. If music is playing when the slideshow is running, information about the
       currently playing music can be displayed.
    5. Multiple slide transition effects can be chosen.
    6. Slides can be displayed dimmed.
