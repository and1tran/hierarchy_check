#!/usr/bin/env python
#SETMODE 777

#----------------------------------------------------------------------------------------#
#------------------------------------------------------------------------------ HEADER --#

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

#----------------------------------------------------------------------------------------#
#----------------------------------------------------------------------------- IMPORTS --#

# Default Python Imports
from PySide2 import QtGui, QtCore, QtWidgets
import os

# External
from gen_utils.pipe_enums import Discipline
from core_tools.pipe_context import PipeContext
from gen_utils.utils import IO
from shotgun_tools.sg_pipe_objects import ProjectFetcher
from shotgun_tools.sg_utils import get_sg_user_projects
from maya_tools.guis.maya_guis import ConfirmDialog
from maya_tools.guis.maya_gui_utils import get_maya_window, make_line
from maya_tools.utils.hierarchy_check_utils import HierarchyCheckUtil

#----------------------------------------------------------------------------------------#
#--------------------------------------------------------------------------- FUNCTIONS --#

#----------------------------------------------------------------------------------------#
#----------------------------------------------------------------------------- CLASSES --#

class HierarchyCheckGUI(QtWidgets.QDialog):
    """
    Class for the GUI.
    """
    def __init__(self, context=None):
        QtWidgets.QDialog.__init__(self, parent=get_maya_window())

        # Essentials for finding a project.
        self.project_reader = ProjectFetcher()
        self.project = None

        # Attributes for assets.
        self.asset_obj  = None
        self.all_assets = None

        # The asset discilpines we'll grab from.
        self.asset_disc_list = [Discipline.MODEL.name,
                                Discipline.RIG.name,
                                Discipline.SURFACE.name]

        if not context:
            self.context = PipeContext.basic()
        else:
            self.context = context

        self.selection_layout = None
        self.line1            = None
        self.model_layout     = None
        self.line2            = None
        self.rig_layout       = None
        self.line3            = None
        self.surface_layout   = None

        self.model_tree_view   = None
        self.rig_tree_view     = None
        self.surface_tree_view = None

        self.rig_icon_lbl     = None
        self.surface_icon_lbl = None
        self.icon_file_names  = ["accept_icon.png", "warning_icon.png", "cancel_icon.png"]
        self.icon_paths       = []

        self.hier_check_util = HierarchyCheckUtil()

    def init_gui(self):
        """
        Builds the GUI that the user will use.
        """
        for icon in self.icon_file_names:
            self.icon_paths.append(self.get_icon_path(icon))

        main_hb = QtWidgets.QHBoxLayout(self)

        # Creates the select layout.
        self.selection_layout = self.create_selection_layout()
        self.line1 = make_line(orientation="vertical")

        # Creates the model layout.
        self.model_layout = self.create_model_layout()
        self.line2 = make_line(orientation="vertical")

        # Creates the rig layout.
        self.rig_layout = self.create_rig_layout()
        self.line3 = make_line(orientation="vertical")

        # Creates the surfacing layout.
        self.surface_layout = self.create_surface_layout()

        # Adds all the elements to the main layout.
        main_hb.addLayout(self.selection_layout)
        main_hb.addWidget(self.line1)
        main_hb.addLayout(self.model_layout)
        main_hb.addWidget(self.line2)
        main_hb.addLayout(self.rig_layout)
        main_hb.addWidget(self.line3)
        main_hb.addLayout(self.surface_layout)

        self.setWindowTitle("Hierarchy Check")
        self.setMinimumSize(800, 200)
        self.show()

    def create_selection_layout(self):
        """
        Builds the selection section of the GUI.

        :return: The selection section.
        :type: QtWidgets.QVBoxLayout
        """
        select_vb = QtWidgets.QVBoxLayout()

        # The project label.
        project_hb = QtWidgets.QHBoxLayout()
        project_lbl = QtWidgets.QLabel("Project:")
        project_hb.addWidget(project_lbl)

        # The project combo box.
        self.project_cb = QtWidgets.QComboBox()
        self.project_cb.addItems(["None"])
        user_projs = get_sg_user_projects()
        if user_projs:
            self.project_cb.addItems(user_projs)
        self.project_cb.currentIndexChanged['QString'].connect(self.project_changed)
        project_hb.addWidget(self.project_cb)
        select_vb.addLayout(project_hb)

        # Make the asset/sequence label and combo box.
        asset_hb = QtWidgets.QHBoxLayout()
        asset_lbl = QtWidgets.QLabel("Asset:")
        self.asset_cb = QtWidgets.QComboBox()
        self.asset_cb.addItems(["None"])
        self.asset_cb.currentIndexChanged['QString'].connect(self.asset_changed)

        asset_hb.addWidget(asset_lbl)
        asset_hb.addWidget(self.asset_cb)
        select_vb.addLayout(asset_hb)

        # Button for deleting existing text documents holding hierarchy info.
        del_curr_btn = QtWidgets.QPushButton("Delete Existing Hierarchy Info")
        del_curr_btn.clicked.connect(self.delete_curr_btn_clicked)
        select_vb.addWidget(del_curr_btn)

        # Button for making text documents holding hierarchy info.
        get_btn = QtWidgets.QPushButton("Get Hierarchy")
        get_btn.clicked.connect(self.get_hierarchies_btn_clicked)
        select_vb.addWidget(get_btn)

        # Isolate the missing geometry in rigging and surfacing with this checkbox.
        self.isolate_check_box = QtWidgets.QCheckBox("Isolate Missing Nodes")
        self.isolate_check_box.clicked.connect(self.isolate_check_box_clicked)
        select_vb.addWidget(self.isolate_check_box)

        select_vb.addStretch(1)

        return select_vb

    def create_model_layout(self):
        """
        Builds the model section of the GUI.

        :return: The model section.
        :type: QtWidgets.QVBoxLayout
        """
        model_vb = QtWidgets.QVBoxLayout()

        # Create simple label.
        model_lbl = QtWidgets.QLabel("Modeling")

        # Create Modeling Tree Widget.
        self.model_tree_view = QtWidgets.QTreeWidget()
        self.model_tree_view.setHeaderLabels(["Groups"])

        model_vb.addWidget(model_lbl)
        model_vb.addWidget(self.model_tree_view)

        return model_vb

    def create_rig_layout(self):
        """
        Builds the rig section of the GUI.

        :return: The rig section.
        :type: QtWidgets.QVBoxLayout
        """
        rig_vb = QtWidgets.QVBoxLayout()

        # Top HBox
        top_hb = QtWidgets.QHBoxLayout()

        # Simple label.
        rig_lbl = QtWidgets.QLabel("Rigging")
        top_hb.addWidget(rig_lbl)

        # Simple label to hold the pass/fail icon.
        self.rig_icon_lbl = QtWidgets.QLabel()
        self.rig_icon_lbl.setAlignment(QtCore.Qt.AlignRight)
        top_hb.addWidget(self.rig_icon_lbl)

        # Rig Tree Widget.
        self.rig_tree_view = QtWidgets.QTreeWidget()
        self.rig_tree_view.setHeaderLabels(["Groups", "Status"])
        self.rig_tree_view.setColumnWidth(0, 200)

        rig_vb.addLayout(top_hb)
        rig_vb.addWidget(self.rig_tree_view)

        return rig_vb

    def create_surface_layout(self):
        """
        Builds the surface section of the GUI.

        :return: The surface section.
        :type: QtWidgets.QVBoxLayout
        """
        surface_vb = QtWidgets.QVBoxLayout()

        # Top HBox
        top_hb = QtWidgets.QHBoxLayout()

        # Simple label.
        surface_lbl = QtWidgets.QLabel("Surfacing")
        top_hb.addWidget(surface_lbl)

        # Simple label to hold the pass/fail icon.
        self.surface_icon_lbl = QtWidgets.QLabel()
        self.surface_icon_lbl.setAlignment(QtCore.Qt.AlignRight)
        top_hb.addWidget(self.surface_icon_lbl)

        # Surfacing Tree Widget.
        self.surface_tree_view = QtWidgets.QTreeWidget()
        self.surface_tree_view.setHeaderLabels(["Groups", "Status"])
        self.surface_tree_view.setColumnWidth(0, 200)

        surface_vb.addLayout(top_hb)
        surface_vb.addWidget(self.surface_tree_view)

        return surface_vb

    def get_icon_path(self, file_name):
        """
        This method gets the icon filepath

        :param file_name: The file name
        :type: str

        :return: The icon path
        :type: str
        """

        icon_dir = "%s/%s" % (PipeContext().eval_path(formula='pr_global_imgs_dir'),
                              "016")

        file_path = icon_dir+'/'+file_name
        if os.path.isfile(file_path):
            return file_path
        return None

    def project_changed(self, item):
        """
        When the project field is changed, the assets box will update.

        :param item: The selection from the combo box.
        :type: QtCore.QString
        """
        # Convert item to a string and verify the input first.
        value = str(item)
        if value == "None":
            self.project = None
            return None

        # We want the project obj b/c we can get the assets and shots from it.
        self.project = self.project_reader.get_project_object(value)

        # Get the assets list and add it to the combo box.
        self.all_assets = self.project.get_asset_names()
        self.asset_cb.clear()
        self.asset_cb.addItems(["None"] + self.all_assets)
        self.asset_cb.setCurrentText("None")
        
    def asset_changed(self, item):
        """
        When the asset field is changed, set the asset object, finds the type, and
        gets the file paths we want to get hierarchies from.

        :param item: The selection from the combo box.
        :type: QtCore.QString
        """
        # Convert item to a string and verify the input first.
        value = str(item)
        if value == "None" or value == "":
            self.asset_obj = None
            return None

        # Get the info for the asset.
        self.asset_obj = self.project.get_asset(value)

    def delete_curr_btn_clicked(self):
        """
        Deletes the existing text documents.

        :return: Success of the operation.
        :type: bool
        """
        # Confirm with the user's selection with a confirmation box.
        title = ("Deleting Existing Hierarchy Data")
        message = "Are you sure you want to delete the current hierarchy data? \n\n" \
                  "You can always use the \"Get Hierarchies\" button to retreive the\n" \
                  "data from the most recent published versions."
        confirm_dialog = ConfirmDialog(message=message, title=title)
        confirm_dialog.init_gui()
        if not confirm_dialog.result:
            return None

        # Send the hierarchy check the asset_obj.
        self.hier_check_util.set_asset_obj(self.asset_obj)

        if not self.hier_check_util.delete_text_files():
            return None

        return True

    def get_hierarchies_btn_clicked(self):
        """
        Gets the file path from the SG obj and gathers the hierarchy using batch_utils.
        """
        # Check if this is an asset.
        if not self.asset_obj.is_asset:
            IO.error("Invalid asset due to missing the asset structure of modeling,"
                     "rigging, and surfacing. Check if this is an assembly.")
            return None

        # Set the utility's asset_obj.
        self.hier_check_util.set_asset_obj(self.asset_obj)

        # Clears the previous tree views.
        self.model_tree_view.clear()
        self.rig_tree_view.clear()
        self.surface_tree_view.clear()

        # Clear's the utility's attributes for the next asset.
        self.hier_check_util.clear_attrs()

        # Send the asset_obj from the GUI to utils.
        if not self.hier_check_util.set_asset_obj(self.asset_obj):
            IO.error("Invalid asset object passed to utils.")
            return None

        # Gets the info for the hier_check_util. Any error will display from utils.
        if not self.hier_check_util.get_info():
            return None

        # Populate the tree with the results.
        self.populate_tree_view()

        # Set the pass, warning, or fail icons for rigging and surfacing.
        self.set_icon()

        return True

    def populate_tree_view(self):
        """
        Populates the tree views.
        """
        # Get the useful lists and dicts from the util.
        rig_fails = self.hier_check_util.get_rig_fail()
        surface_fails = self.hier_check_util.get_surface_fail()
        read_hier = self.hier_check_util.get_read_hiers()

        for curr_disc in self.asset_disc_list:
            # Check if it exists in the dictionary. Any txt that doesn't exist already
            # got an error message.
            if not read_hier[curr_disc]:
                continue

            # Make the root "geometry_GRP", and parent to the respective view.
            tree_view = None
            if curr_disc == Discipline.MODEL.name:
                tree_view = self.model_tree_view
            elif curr_disc == Discipline.RIG.name:
                tree_view = self.rig_tree_view
            elif curr_disc == Discipline.SURFACE.name:
                tree_view = self.surface_tree_view
            root = QtWidgets.QTreeWidgetItem(tree_view,
                                             [read_hier[curr_disc][0][1:], ""])

            # Iterate through everything past the first element, adding the items that
            # failed. B/c the items that failed are in modeling not in rig or surfacing.
            list_items = read_hier[curr_disc][1:]
            if curr_disc == Discipline.RIG.name:
                list_items += rig_fails
            elif curr_disc == Discipline.SURFACE.name:
                list_items += surface_fails

            # Make lists that will hold the names and tree widget items so they
            # can be parents to other QTreeWidgetItems. The first is "geometry_GRP".
            temp_grp_names = [read_hier[curr_disc][0].split("|")]
            temp_grp_tree_widget_list = [root]
            for item in list_items:

                # First split the string without the dividers into a list.
                # Looks like ['', 'geometry_GRP', 'ren_GRP', 'pCylinder_REN']
                item_split = item.split("|")
                # Keep the parent as a list b/c the entire list leads up to the item
                # so we use a pointer to the list as a unique identifier for the parent.
                item_parent_list = item_split[:-1]
                # Use the parent list to find the index from the temp_grp_names.
                parent_index = temp_grp_names.index(item_parent_list)

                # Make the TreeWidgetItem, parent it to the parent_index we found.
                entry = QtWidgets.QTreeWidgetItem(temp_grp_tree_widget_list\
                                                    [parent_index], [item_split[-1], ""])
                entry.setExpanded(True)

                # Save the current list to an overall list so we can reference the tree
                # widget item later if it happens to be a parent.
                temp_grp_names.append(item_split)
                temp_grp_tree_widget_list.append(entry)

                # Sets the background depending if they kept the hierarchy.
                # Sets rigging or surfacing if they didn't conform.
                if curr_disc == Discipline.MODEL.name:
                    continue
                if curr_disc == Discipline.RIG.name:
                    if item in rig_fails:
                        entry.setBackground(1, QtGui.QBrush(QtGui.QColor('darkRed')))
                if curr_disc == Discipline.SURFACE.name:
                    if item in surface_fails:
                        entry.setBackground(1, QtGui.QBrush(QtGui.QColor('darkRed')))

            root.setExpanded(True)

    def isolate_check_box_clicked(self):
        """
        Isolates the missing nodes in rigging and surfacing.
        """
        # If checked, then hide whatever is in rig and surfacing.
        if self.isolate_check_box.checkState():
            root = self.rig_tree_view.invisibleRootItem()
            if root.childCount() > 0:
                self._isolate_checked(root)

            root = self.surface_tree_view.invisibleRootItem()
            if root.childCount() > 0:
                self._isolate_checked(root)

        # Otherwise reveal all items in the tree views.
        else:
            root = self.rig_tree_view.invisibleRootItem()
            if root.childCount() > 0:
                self._reveal_hidden(root)

            root = self.surface_tree_view.invisibleRootItem()
            if root.childCount() > 0:
                self._reveal_hidden(root)

    def _isolate_checked(self, parent):
        """
        Recursively go through the hierarchy finding any children that are red will skip
        this parent. If there are no red in the child hierarchy that means this parent is
        find to hide.

        :param parent: The parent we will get the child count from.
        :type: QtWidgets.QTreeWidgetItem
        """
        # The base case. If this item is red, then return False because it informs
        # the parent whether to hide. Otherwise hide then return True.
        if not parent.childCount() > 0:
            if parent.backgroundColor(1) == QtGui.QColor('darkRed'):
                return False
            else:
                parent.setHidden(True)
                return True

        # There are children to check.
        else:
            child_count = parent.childCount()
            # This list will determine if this parent will hide or not.
            pass_list = []
            for child_index in range(child_count):
                pass_list.append(self._isolate_checked(parent.child(child_index)))
            if False in pass_list:
                return False
            else:
                parent.setHidden(True)
                return True

    def _reveal_hidden(self, parent):
        """
        Recursively go through the hierarchy finding any parent, unhiding it, then
        going into the children and unhiding all of them.
        """
        # The base case. This is the leaf so unhide it if it's hidden.
        if not parent.childCount() > 0:
                parent.setHidden(False)

        # The parent has children, so unhide this then dive into the children to unhide.
        else:
            parent.setHidden(False)
            child_count = parent.childCount()
            for child_index in range(child_count):
                self._reveal_hidden(parent.child(child_index))

    def set_icon(self):
        """
        Sets the icon of rigging and surfacing after they've populated their views.
        Passing means no fails - so green check mark.
        Unable to find a rigging or surfacing - warning mark.
        Fails present, meaning modeling was missing - red X.
        """
        # Gets the rig and surface fails from the check utility.
        rig_fails = self.hier_check_util.get_rig_fail()
        surface_fails = self.hier_check_util.get_surface_fail()
        read_hier = self.hier_check_util.get_read_hiers()

        # First check if we read anything for rigging, then checks if rigging failed.
        if not read_hier[Discipline.RIG.name]:
            self.rig_icon_lbl.setPixmap(self.icon_paths[1])
        elif not rig_fails:
            self.rig_icon_lbl.setPixmap(self.icon_paths[0])
        else:
            self.rig_icon_lbl.setPixmap(self.icon_paths[2])

        # First check if we read anything for surfacing, then checks if surfacing failed.
        if not read_hier[Discipline.SURFACE.name]:
            self.surface_icon_lbl.setPixmap(self.icon_paths[1])
        elif not surface_fails:
            self.surface_icon_lbl.setPixmap(self.icon_paths[0])
        else:
            self.surface_icon_lbl.setPixmap(self.icon_paths[2])