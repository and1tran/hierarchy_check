#!/usr/bin/env python
# SETMODE 777

# ----------------------------------------------------------------------------------------#
# ------------------------------------------------------------------------------ HEADER --#

"""
:author:
    Andy Tran - axt170020

:synopsis:
    A one line summary of what this module does.

:description:
    A detailed description of what this module does.

:applications:
    Any applications that are required to run this script, i.e. Maya.

:see_also:
    Any other code that you have written that this module is similar to.
"""

# ----------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------- IMPORTS --#

# Default Python Imports
import subprocess
import os
import time

# External
import maya.cmds as cmds
from gen_utils.pipe_enums import Discipline
from core_tools.pipe_context import PipeContext
from gen_utils.utils import IO
from maya_tools.utils.maya_enums import NamingConventionEnums
from gen_utils.pipe_enums import RigTypes


# ----------------------------------------------------------------------------------------#
# --------------------------------------------------------------------------- FUNCTIONS --#

def store_hierarchy(disc=None, output_dir=None):
    """
    Gets information from the maya ascii file and stores it into a txt.

    :param disc: What discipline will this store the hierarchy from.
    :type: str

    :param output_dir: The file path to write the text file.
    :type: str
    """
    # Get the start of the modeling hierarchy from enums, we're expecting geometry_GRP.
    # If this is rigging, we're looking for just "geometry_GRP", modeling and surfacing
    # can work with "|geometry_GRP"
    root = NamingConventionEnums().MODEL_HIERARCHY[0] if not disc == "rig" \
        else NamingConventionEnums().RIG_HIERARCHY[5]
    root_node = cmds.ls(root)

    # Verify the root node exists and its one of a kind in the scene.
    if not root_node:
        return None
    elif len(root_node) > 1:
        return None

    # Gets all the descendents of the root node. Add the root to the descendants list.
    # If this is rigging then take care of the prefixes.
    children = cmds.listRelatives(root_node, allDescendents=True, fullPath=True,
                                  children=True, type="transform")
    children.sort()
    geo_GRP_nodes = [root] + children
    if disc == "rig":
        geo_GRP_nodes = cut_rig_prefixes(geo_GRP_nodes)

    # Create the document and name it after the discipline.
    file1 = open("%s" % output_dir, "w")
    # We'll make a string for the txt starting with the root node.
    write_str = ""
    # Add all the descendents of the root node to the txt string
    for node in geo_GRP_nodes:
        write_str += "%s\n" % node

    # Write the txt string and ends the command.
    file1.write(write_str)
    file1.close()

    cmds.quit(force=True)

    return True

def cut_rig_prefixes(nodes_list=None):
    """
    In rigging it gives "|master|geometry_GRP|..." and this function removes those
    prefixes leaving just "|geometry_GRP|..." like modeling and surfacing.

    :param nodes_list: The names we got from the rig file under geometry_GRP.
    :type: list
    """
    # Runs through each item and cuts the master geometry leading just to |geometry_GRP.
    return_list = []
    for node in nodes_list:
        return_list.append(node.split("%s" % \
                                      NamingConventionEnums().RIG_HIERARCHY[4], 1)[1])

    return return_list

# ----------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------- CLASSES --#

class HierarchyCheckUtil(object):
    """
    Class for the GUI.
    """
    ASSET_DIR = "as_pub_official_dir"

    def __init__(self, context=None):

        # Attributes for assets.
        self.asset_obj = None

        self.asset_disc_list = [Discipline.MODEL.name,
                                Discipline.RIG.name,
                                Discipline.SURFACE.name]

        if not context:
            self.context = PipeContext.basic()
        else:
            self.context = context

        self.maya_file_paths = {}
        self.text_file_paths = {}
        self.read_hier       = {}
        self.rig_fail        = []
        self.surface_fail    = []

    def get_read_hiers(self):
        """
        Returns the read hierarchies for all disciplines, assuming there is stuff to
        return.

        :return: The dictionary of what was read from the hierarchies. It should look
                 like this:
                 A dictionary with the file paths to the text documents
                 {"model":   "\\infinity.utdallas.edu\store\asset\model\asset_hier.txt",
                  "rig":     "\\infinity.utdallas.edu\store\asset\ani_rig\asset_hier.txt",
                  "surface": "\\infinity.utdallas.edu\store\asset\surface\asset_hier.txt"}
        :type: dict
        """
        # If we got nothing from modeling, there's no point in displaying anything.
        if not self.read_hier[Discipline.MODEL.name]:
            return None

        return self.read_hier

    def get_rig_fail(self):
        """
        Returns the list of nodes missing in rigging that were present in modeling.

        :return: The list of modeling nodes that weren't found in rigging.
        :type: list
        """
        return self.rig_fail

    def get_surface_fail(self):
        """
        Returns the list of nodes missing in surfacing that were present in modeling.

        :return: The list of modeling nodes that weren't found in surfacing.
        :type: list
        """
        return self.surface_fail

    def clear_attrs(self):
        """
        Clears the attributes for the utility so a new object can be under the microscope.
        """
        self.text_file_paths.clear()
        self.read_hier.clear()
        self.rig_fail.clear()
        self.surface_fail.clear()

    def get_maya_files(self):
        """
        Gets the maya files we will grab the hierarchies from.
        """
        # Gets the necessary files in case we need to create the text files.
        self.maya_file_paths[self.asset_disc_list[0]] = \
            self.asset_obj.get_official_model_file()
        self.maya_file_paths[self.asset_disc_list[1]] = \
            self.asset_obj.get_official_rig_file(rig_type=RigTypes.ANI)
        self.maya_file_paths[self.asset_disc_list[2]] = \
            self.asset_obj.get_active_surface_file()

    def set_asset_obj(self, asset_obj):
        """
        Sets the utility's SG asset obj.

        :param asset_obj: The SG asset obj retreived from the GUI.
        :type: SG Asset Obj
        """
        if not asset_obj:
            return None

        # We don't need to validate input b/c the GUI does that.
        self.asset_obj = asset_obj

        return True

    def get_info(self):
        """
        Gets the info from the Maya scenes, put it into text files, and read those text
        files for the GUI.
        """
        # Gets the necessary files in case we need o create the text files.
        self.get_maya_files()

        # Check if the text files exist and create if they don't.
        if not self.check_for_text_files(create=True):
            IO.error("No valid asset selected.")
            return None

        # Gets hierarchy info from the text files.
        self.get_text_info()

        # Figures out what is missing from modeling to rigging and surfacing.
        if not self.match_items():
            return None

        return True

    def delete_text_files(self):
        """
        Deletes the existing text documents. Confirming with deleting is with the user.
        """
        # Gathers the text documents.
        if not self.check_for_text_files(create=False):
            IO.error("No text files to delete.")
            return None

        # Iterate through the text file paths found and try to delete them.
        for curr_disc in self.text_file_paths:
            curr_doc = self.text_file_paths[curr_disc]
            if curr_doc == None:
                continue
            try:
                os.remove(curr_doc)
            except WindowsError or OSError:
                IO.error("Unable to delete: \n%s" % curr_doc)
                continue

        return True

    def check_for_text_files(self, create=True):
        """
        Checks if the text files exist. If they don't, then choose to make it
        with the maya batch or leave it as None.

        :param create: The flag used to check if we want to create the text file if it
                       doesn't exist. An example where we want to choose is
                       deleting old text files. We only want to know whether the text
                       files exist to delete the old one, but not create one if it
                       doesn't exist.
        :type: bool

        :return: A dictionary with the file paths to the text documents
                 {"model": "\\infinity.utdallas.edu\store\asset\model\asset_hier.txt",
                  "rig": "\\infinity.utdallas.edu\store\asset\ani_rig\asset_hier.txt",
                  "surface": "\\infinity.utdallas.edu\store\asset\surface\asset_hier.txt"}
        :type: dict
        """
        # Check if we have an asset we can work with.
        if not self.asset_obj:
            return None

        # Make the kwargs dictionary for context to find the file path.
        kwargs = {"project": self.asset_obj.project_name}
        kwargs["asset"] = self.asset_obj.name
        kwargs["asset_type"] = self.asset_obj.type

        # Check if each discipline has a text file. Change kwargs["publish_type"] each
        # time to account for the discipline. Rigging will check "ani_rig", not just "rig.
        for curr_disc in self.asset_disc_list:
            kwargs["publish_type"] = RigTypes.ANI if curr_disc == self.asset_disc_list[1] \
                else curr_disc
            dir_path = self.context.eval_path(formula=self.ASSET_DIR, **kwargs)
            output_txt = "%s/%s_hier.txt" % (dir_path, self.asset_obj.name)

            if not os.path.exists(output_txt):
                # Ensure we want to create the text file.
                if create == False:
                    self.text_file_paths[curr_disc] = None
                    continue
                # Check if the maya file we're pulling the hierarchy from exists.
                if not os.path.exists(self.maya_file_paths[curr_disc]):
                    IO.warning("No official %s was found." % curr_disc)
                    self.text_file_paths[curr_disc] = None
                    continue
                # Try to make the text file.
                IO.info("Creating the %s %s hier file at \n%s" % (self.asset_obj.name, \
                                                                  curr_disc, output_txt))
                if not self.maya_batch_create_txt(curr_disc,
                                                  self.maya_file_paths[curr_disc],
                                                  output_txt):
                    IO.error("Was not able to create the files, took too long.")
                    continue

            # If the discipline already has a text file, add it to the list and continue.
            else:
                IO.success("Found the %s %s hier file at \n%s" % (self.asset_obj.name, \
                                                                  curr_disc, output_txt))
                self.text_file_paths[curr_disc] = output_txt

        return self.text_file_paths

    def maya_batch_create_txt(self, asset_disc=None, maya_file_path=None,
                              export_file_path=None):
        """
        Starts a maya batch instance to create the text file storing the hierarchy.

        :param asset_disc: The discipline of the asset.
        :type: str

        :param maya_file_path: The maya file to take the hierarchy from.
        :type: str

        :param export_file_path: The output file path. Expecting the asset's published
                                 directories.
        :type: str

        :return: Success of the operation.
        :type: bool
        """
        # MEL is automatically run so we use "python("")" to run python code.
        maya_cmd = ("python(\\\"import maya.cmds as cmds;"
                    "import maya_tools.utils.hierarchy_check_utils as hkUtil;"
                    "hkUtil.store_hierarchy(\'%s\',\'%s\');\\\")" \
                    % (asset_disc, export_file_path))

        cmd = ('mayabatch -file %s -command "%s"' % (maya_file_path, maya_cmd))

        # Try to create the file within 15 seconds.
        output = None
        try:
            output = subprocess.Popen(cmd, shell=True, start_new_session=True)
            output.wait(timeout=15)
        except subprocess.CalledProcessError:
            IO.error("Error creating file.")
            return None
        except subprocess.TimeoutExpired:
            # We want the timer to finish from the subprocess, but the timer finishes
            # with an exception, so catch it here. We check if the maya batch created
            # the file every 15 secs, for 10 times so after 3 minutes.
            counter = 0
            while not os.path.exists(export_file_path) and counter < 10:
                IO.info("Still creating the file...")
                time.sleep(15)
                counter += 1
            # If the text file was created then add to the file paths dict.
            if os.path.exists(export_file_path):
                IO.success("Created the %s file, continuing the program." % asset_disc)
                self.text_file_paths[asset_disc] = export_file_path
            else:
                IO.error("%s txt file was not created" % asset_disc)
                return None
        finally:
            self.kill(output)  # Always kill the maya batches at the end.

        return self.text_file_paths

    def kill(self, process):
        """
        Will clean up the maya batches that created the file to save RAM. Maya batches
        are supposed to close on their own, but to erase them completely, we'll just
        kill it manually.

        :param process: The process object running maya batch.
        :type: subprocess
        """
        if os.name == "nt":
            os.system("wmic process where name=\"mayabatch.exe\" call terminate")
        else:
            process.terminate()

    def get_text_info(self):
        """
        Gets the information from the output text. Input validation is handled in
        the functions before this one is called.
        """
        for curr_disc in self.asset_disc_list:
            self.read_hier[curr_disc] = []

            # Check if there is a text file in the list and whether it exists.
            if not self.text_file_paths[curr_disc] or \
                    not os.path.exists(self.text_file_paths[curr_disc]):
                continue
            elif os.path.getsize(self.text_file_paths[curr_disc]) == 0:
                IO.error("%s.txt does not have contents" % curr_disc)
                continue

            # Get back the contents of the txt as a list.
            file1 = open(self.text_file_paths[curr_disc], "r")
            readlines = file1.readlines()

            # Cut the \n at the end of all elements and put into the held list.
            for line in readlines:
                line = line.rstrip("\n")
                self.read_hier[curr_disc].append(line)

    def match_items(self):
        """
        Checks if an item from model matches in rigging and surfacing. We don't care
        about extra items in rigging or surfacing. We only check exactly what was
        from modeling.

        :return: Success of the operation.
        :type: bool
        """
        # Check if anything is in the published model, rigging, and working surfacing.
        if not self.read_hier[Discipline.MODEL.name]:
            IO.warning("We did not get anything from the official modeling, quitting...")
            return None
        if not self.read_hier[Discipline.RIG.name] and not \
                self.read_hier[Discipline.SURFACE.name]:
            return None
        # Simple loop through all the modeling items matching to rigging items.
        if self.read_hier[Discipline.RIG.name]:
            for item in self.read_hier[Discipline.MODEL.name]:
                if not (item in self.read_hier[Discipline.RIG.name]):
                    self.rig_fail.append(item)

        # Simple loop through all the modeling items matching to surfacing items.
        if self.read_hier[Discipline.SURFACE.name]:
            for item in self.read_hier[Discipline.MODEL.name]:
                if not (item in self.read_hier[Discipline.SURFACE.name]):
                    self.surface_fail.append(item)

        return True