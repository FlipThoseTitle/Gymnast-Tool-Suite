'''
    Gymnast Tool Suite
    Copyright (C) 2025 FlipThoseTitle

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

if "bpy" not in locals():
    from . import animationPanel
    from . import modelPanel
    from . import xmlPanel
else:
    import importlib

    importlib.reload(animationPanel)
    importlib.reload(modelPanel)
    importlib.reload(xmlPanel)

bl_info = {
    "name": "Gymnast Tool Suite",
    "description": "Create Custom Animation and Model for Vector and Shadow Fight 2",
    "author": "FlipThoseTitle",
    "version": (0, 9),
    "blender": (4, 4, 0),
    "location": "View3D > Panels > Gymnast Tool Suite",
    "category": "Object",
    "wiki_url": "https://github.com/FlipThoseTitle/Gymnast-Tool-Suite",
    "tracker_url": "https://github.com/FlipThoseTitle/Gymnast-Tool-Suite/issues",
}

import bpy

classes = [animationPanel, modelPanel, xmlPanel]

def register():
    for c in classes:
        c.register()

def unregister():
    for c in reversed(classes):
        c.unregister()
        
if __name__ == "__main__":
    register()
