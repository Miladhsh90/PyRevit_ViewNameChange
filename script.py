# -*- coding: utf-8 -*-
"""
Finds all views on sheets with 'Framing Elevation' in their name
and prompts the user to rename them one by one.
"""

from pyrevit import revit, DB, forms, script

# Get the current Revit document
doc = revit.doc

# --- 1. Find all unique "Framing Elevation" views placed on sheets ---
# Use a dictionary to store unique views to avoid processing the same view twice
# The key will be the view's ElementId, and the value will be the View element
framing_elevation_views = {}

# Collect all sheets in the project
sheets = DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet)\
                                         .WhereElementIsNotElementType()\
                                         .ToElements()

# Iterate over each sheet to find its viewports
for sheet in sheets:
    # Get all viewport element IDs on the current sheet
    viewport_ids = sheet.GetAllViewports()
    if not viewport_ids:
        continue

    for vp_id in viewport_ids:
        # Get the view associated with the viewport
        view_id = doc.GetElement(vp_id).ViewId
        
        # Ensure the view ID is valid and we haven't already processed this view
        if view_id != DB.ElementId.InvalidElementId and view_id not in framing_elevation_views:
            view = doc.GetElement(view_id)
            # Check if the element is a View and its name is an exact match
            if view and view.Name == "Framing Elevation":
                framing_elevation_views[view_id] = view

# --- 2. Check if any views were found and exit if not ---
if not framing_elevation_views:
    forms.alert("No 'Framing Elevation' views were found on any sheets.",
                title="No Views Found")
    script.exit()

# --- 3. Get a new base name from the user ONCE ---
new_base_name = forms.ask_for_string(
    default="Framing Elevation Old",
    prompt="Enter the new base name for the views.\n"
           "A number will be appended automatically (e.g., New Name - 1).",
    title="Batch Rename Views"
)

# If user cancels, exit the script gracefully
if not new_base_name:
    forms.alert("Operation cancelled. No views were renamed.", title="Cancelled")
    script.exit()

# --- 4. Iterate through the collected views and rename them ---
renamed_count = 0
counter = 1
views_to_process = framing_elevation_views.values()

# Use a Transaction Group to bundle all renames into a single undo-able action
with DB.TransactionGroup(doc, "Batch Rename Framing Elevations") as tg:
    tg.Start()

    for view in views_to_process:
        # Construct the new unique name by appending the counter
        final_new_name = "{} - {}".format(new_base_name, counter)
        try:
            # Start a sub-transaction for the individual rename operation
            with DB.Transaction(doc, "Rename View") as t:
                t.Start()
                view.Name = final_new_name
                t.Commit()
            renamed_count += 1
            counter += 1  # Increment counter for the next view
        except Exception as e:
            forms.alert("Failed to rename view '{}'.\nError: {}".format(view.Name, e), title="Error")
            tg.RollBack()  # Abort the entire operation
            script.exit()

    # If the loop completes successfully, commit the transaction group
    tg.Assimilate()

# --- 4. Show a final report to the user ---
if renamed_count > 0:
    forms.alert("Successfully renamed {} view(s).".format(renamed_count),
                title="Process Complete")
else:
    forms.alert("No views were renamed.",
                title="Process Complete")
