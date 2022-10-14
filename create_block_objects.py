import arcpy.management
import config
import utility
import os

log_obj = utility.Logger(config.log_file)
log_obj.info("Create Block Objects - starting".format())

arcpy.env.overwriteOutput = True

# data prep

log_obj.info("Create Block Objects - formatting ARC_ROW".format())
key_field = "LOCALID"
ARC_ROW_dissolve = arcpy.management.Dissolve(config.ARC_ROW, r"in_memory\ARC_ROW_diss", key_field)


utility.add_field_if_needed(ARC_ROW_dissolve, "STREETNAME", "TEXT", length=50)
utility.get_and_assign_field_value_from_dict(config.ARC_ROW,
                                             key_field,
                                             "STREETNAME",
                                             ARC_ROW_dissolve,
                                             key_field,
                                             "STREETNAME")


log_obj.info("Create Block Objects - creating centerline based allocation areas".format())
arcpy.CheckOutExtension("Spatial")
allocation_raster = arcpy.sa.EucAllocation(config.street_centerlines, '', '', 5, key_field, '', r"in_memory\allocation_raster")
allocation_vector = arcpy.RasterToPolygon_conversion(allocation_raster, r"in_memory\allocation_vector", "NO_SIMPLIFY", 'Value')
# gridcode = LOCALID (ie the ROW ID)


# assign ROW to lots (first pass)
log_obj.info("Create Block Objects -    spatial join 1".format())
buffer_distance_ft = 3
ROW_to_TL_sj_1to1 = arcpy.SpatialJoin_analysis(config.taxlots,
                                          ARC_ROW_dissolve,
                                          r"in_memory\ROW_to_TL_sj_1to1",
                                          "JOIN_ONE_TO_ONE",
                                          "KEEP_COMMON",
                                          "#",
                                          "INTERSECT",
                                          buffer_distance_ft)

utility.add_field_if_needed(ROW_to_TL_sj_1to1, "Join_Count_1to1", "SHORT")
with arcpy.da.UpdateCursor(ROW_to_TL_sj_1to1, ["Join_Count", "Join_Count_1to1"]) as cursor:
    for row in cursor:
        if row[0] is not None:
            row[1] = row[0]
            cursor.updateRow(row)

keep_fields = ["PROPERTYID", "SITEADDR", "Join_Count_1to1"]
utility.delete_fields(ROW_to_TL_sj_1to1, keep_fields)

log_obj.info("Create Block Objects -    spatial join 2".format())
ROW_to_TL_sj_1toM = arcpy.SpatialJoin_analysis(ROW_to_TL_sj_1to1,
                                          ARC_ROW_dissolve,
                                          r"in_memory\ROW_to_TL_sj_1toM",
                                          "JOIN_ONE_TO_MANY",
                                          "KEEP_COMMON",
                                          "#",
                                          "INTERSECT",
                                          buffer_distance_ft)

keep_fields = ["PROPERTYID", "SITEADDR", "Join_Count_1to1", "LOCALID", "STREETNAME"]
utility.delete_fields(ROW_to_TL_sj_1toM, keep_fields)

log_obj.info("Create Block Objects - add and populate ADDR_match".format())
utility.add_field_if_needed(ROW_to_TL_sj_1toM, "ADDR_match", "SHORT")
with arcpy.da.UpdateCursor(ROW_to_TL_sj_1toM, ['SITEADDR', 'STREETNAME', 'ADDR_match']) as cursor:
    for row in cursor:
       if row[0] is not None and row[1] is not None:
          if row[1] in row[0]:
             row[2] = 1
          else:
             row[2] = 0
       elif row[0] is None or row[1] is None:
           row[2] = 0
       cursor.updateRow(row)

log_obj.info("Create Block Objects - assign ROW ID values to taxlots per spatial match (address not considered)".format())
spatial_only_FL = arcpy.MakeFeatureLayer_management(ROW_to_TL_sj_1toM, r"in_memory\spatial_FL", "LOCALID is not Null and Join_Count_1to1 = 1")
spatial_only = arcpy.CopyFeatures_management(spatial_only_FL, r"in_memory\spatial_only")

print(arcpy.GetCount_management(spatial_only))

utility.get_and_assign_field_value_and_set_process_source(spatial_only,
                                                          "PROPERTYID",
                                                          "LOCALID",
                                                          config.taxlots,
                                                          "PROPERTYID",
                                                          "LOCALID",
                                                          "spatial only")


log_obj.info("Create Block Objects - assign ROW ID values to taxlots per spatial match + address match".format())
spatial_plus_address_FL = arcpy.MakeFeatureLayer_management(ROW_to_TL_sj_1toM, r"in_memory\spatial_plus_address_FL", "LOCALID is not Null and Join_Count_1to1 > 1 and ADDR_match = 1")
spatial_plus_address = arcpy.CopyFeatures_management(spatial_plus_address_FL, r"in_memory\spatial_plus_address")

print(arcpy.GetCount_management(spatial_plus_address))

utility.get_and_assign_field_value_and_set_process_source(spatial_plus_address,
                                                          "PROPERTYID",
                                                          "LOCALID",
                                                          config.taxlots,
                                                          "PROPERTYID",
                                                          "LOCALID",
                                                          "spatial + address match")


log_obj.info("Create Block Objects - assign ROW ID values to taxlots per majority allocation".format())
unassigned_TL_FL = arcpy.MakeFeatureLayer_management(config.taxlots, r"in_memory\unassigned_TL_FL", "LOCALID is Null")
unassigned_TL = arcpy.CopyFeatures_management(unassigned_TL_FL, r"in_memory\unassigned_FL")

print(arcpy.GetCount_management(unassigned_TL))

unassigned_to_points = arcpy.FeatureToPoint_management(unassigned_TL, r"in_memory\unassigned_to_points", "CENTROID")
point_allocation_sect = arcpy.Intersect_analysis([unassigned_to_points, allocation_vector], r"in_memory\point_allocation_sect", "#", "#", "POINT")

utility.get_and_assign_field_value_and_set_process_source(point_allocation_sect,
                                                          "PROPERTYID",
                                                          "gridcode",
                                                          config.taxlots,
                                                          "PROPERTYID",
                                                          "LOCALID",
                                                          "majority allocation")


log_obj.info("Create Block Objects - merge taxlots and ROW".format())
TL_ROW_merge = arcpy.Merge_management([config.taxlots, ARC_ROW_dissolve], r"in_memory\TL_ROW_merge")

utility.add_field_if_needed(TL_ROW_merge, "block_object_ID", "LONG")
with arcpy.da.UpdateCursor(TL_ROW_merge, ["LOCALID", "block_object_ID"]) as cursor:
    for row in cursor:
        if row[0] != None:
            row[1] = row[0]
        cursor.updateRow(row)

log_obj.info("Create Block Objects - dissolve result - create final block object result".format())
TL_ROW_diss = arcpy.Dissolve_management(TL_ROW_merge, r"in_memory\TL_ROW_diss", "block_object_ID")

log_obj.info("Create Block Objects - adding Color".format())
utility.add_field_if_needed(TL_ROW_diss, "Color", "SHORT")
with arcpy.da.UpdateCursor(TL_ROW_diss, ["Color"]) as cursor:
    counter = 1
    for row in cursor:
        if counter < 11:
            row[0] = counter
            counter = counter + 1
        else:
            counter = 1
            row[0] = counter
            counter = counter + 1
        cursor.updateRow(row)

log_obj.info("Create Block Objects - writing to disk".format())
arcpy.CopyFeatures_management(config.taxlots, os.path.join(config.output_gdb, "TEST_intermediate_taxlots"))
arcpy.CopyFeatures_management(ROW_to_TL_sj_1toM, os.path.join(config.output_gdb, "TEST_ROW_to_TL_sj_1toM"))
arcpy.CopyFeatures_management(TL_ROW_diss, os.path.join(config.output_gdb, "TEST_block_objects"))

log_obj.info("Create Block Objects - done".format())