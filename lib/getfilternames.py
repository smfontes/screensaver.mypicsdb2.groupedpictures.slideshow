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

# This script queries the plugin.image.mypicsdb2 database to get a list of saved filter names.
# It then stores the filter names as selectable options in this addon's settings.xml file.

import os.path

import xbmc
import xbmcaddon

import xml.etree.ElementTree as ET
import mypicsdb.MypicsDB  as MypicsDB

# Get a list of all of the filter names
MPDB = MypicsDB.MyPictureDB()
query = """Select strFilterName FROM FilterWizard"""
filter_names_list = MPDB.cur.request(query)
filter_names = [name[0] for name in filter_names_list]

# Find where to insert the filter names in the settings.xml file
settings_file = os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'resources', "settings.xml")
tree = ET.ElementTree(file=settings_file)
options = tree.find(".//*setting[@id='filtername']/constraints/options")

# Remove existing filter names so we don't keep duplicationg existing filter names
for option in options.findall('option'):
    options.remove(option)

# Add all of the filter names to settings.xml
for filter_name in filter_names:
    option=ET.SubElement(options,'option')
    option.text=filter_name

# Add first filter name as default value if there are any filters
if len(filter_names) > 0:
    default = tree.find(".//*setting[@id='filtername']/default")
    default.text=filter_names[0]
    
tree.write(settings_file)

# Notify that you must exit from settings and return to see any new filter names
heading = xbmcaddon.Addon().getLocalizedString(30030) 
message = xbmcaddon.Addon().getLocalizedString(30031) 
xbmc.executebuiltin('Notification('+heading+','+message+',10000)')
