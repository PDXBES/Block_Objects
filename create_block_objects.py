import arcpy.management
import config
import utility
import os

log_obj = utility.Logger(config.log_file)
log_obj.info("Create Block Objects - starting".format())


# data prep

log_obj.info("Create Block Objects - formatting ARC_ROW".format())
key_field = "LOCALID"
ARC_ROW_dissolve = arcpy.management.Dissolve(config.ARC_ROW, r"in_memory\ARC_ROW_diss", key_field)
arcpy.JoinField_management(ARC_ROW_dissolve, key_field, config.ARC_ROW, key_field, ["STREETNAME"])

log_obj.info("Create Block Objects - creating centerline based allocation areas".format())
arcpy.CheckOutExtension("Spatial")
allocation_raster = arcpy.sa.EucAllocation(config.street_centerlines, '', '', 5, key_field, '', r"in_memory\allocation_raster")
allocation_vector = arcpy.RasterToPolygon_conversion(allocation_raster, r"in_memory\allocation_vector", "NO_SIMPLIFY", 'Value')
# gridcode = LOCALID (ie the ROW ID)


# assign ROW to lots (first pass)
log_obj.info("Create Block Objects -    spatial join 1".format())
buffer_distance_ft = 3
ROW_to_TL_sj_1to1 = arcpy.SpatialJoin_analysis(config.taxlots,
                                          config.ARC_ROW,
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
                                          config.ARC_ROW,
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

log_obj.info("Create Block Objects - assign ROW ID values to taxlots per spatial match".format())
arcpy.SelectLayerByAttribute_management(ROW_to_TL_sj_1toM, "NEW_SELECTION", "LOCALID is not Null and Join_Count_1to1 = 1")

#input_dict = utility.get_field_value_as_dict(ROW_to_TL_sj_1toM, "PROPERTYID", "LOCALID")
#utility.assign_field_value_from_dict_and_set_process_source(input_dict, config.taxlots,"PROPERTYID", "LOCALID", "spatial only")
utility.get_and_assign_field_value_and_set_process_source(ROW_to_TL_sj_1toM,
                                                          "PROPERTYID",
                                                          "LOCALID",
                                                          config.taxlots,
                                                          "PROPERTYID",
                                                          "LOCALID",
                                                          "spatial only")

arcpy.SelectLayerByAttribute_management(ROW_to_TL_sj_1toM, "CLEAR_SELECTION")

log_obj.info("Create Block Objects - assign ROW ID values to taxlots per spatial match + address match".format())
arcpy.SelectLayerByAttribute_management(ROW_to_TL_sj_1toM, "NEW_SELECTION", "LOCALID is not Null and Join_Count_1to1 > 1 and ADDR_match = 1")

#input_dict = utility.get_field_value_as_dict(ROW_to_TL_sj_1toM, "PROPERTYID", "LOCALID")
#utility.assign_field_value_from_dict_and_set_process_source(input_dict, config.taxlots,"PROPERTYID", "LOCALID", "spatial + address match")
utility.get_and_assign_field_value_and_set_process_source(ROW_to_TL_sj_1toM,
                                                          "PROPERTYID",
                                                          "LOCALID",
                                                          config.taxlots,
                                                          "PROPERTYID",
                                                          "LOCALID",
                                                          "spatial + address match")

arcpy.SelectLayerByAttribute_management(ROW_to_TL_sj_1toM, "CLEAR_SELECTION")

log_obj.info("Create Block Objects - assign ROW ID values to taxlots per majority allocation".format())
# get the taxlots that were assigned either by spatial only or spatial + address match
arcpy.SelectLayerByAttribute_management(ROW_to_TL_sj_1toM, "NEW_SELECTION", "LOCALID is not Null and Join_Count_1to1 > 1 and ADDR_match = 1 or LOCALID is not Null and Join_Count_1to1 = 1")
selection_copy = arcpy.CopyFeatures_management(ROW_to_TL_sj_1toM, r"in_memory\selection_copy")
arcpy.SelectLayerByAttribute_management(ROW_to_TL_sj_1toM, "CLEAR_SELECTION")

# get the taxlots that did not get assigned a LOCALID
arcpy.SelectLayerByAttribute_management(ROW_to_TL_sj_1toM, "NEW_SELECTION", "ADDR_match = 0")
arcpy.SelectLayerByLocation_management(ROW_to_TL_sj_1toM, "ARE_IDENTICAL_TO", selection_copy, "#", "REMOVE_FROM_SELECTION")

remainder_to_points = arcpy.FeatureToPoint_management(ROW_to_TL_sj_1toM, r"in_memory\remainder_to_points", "CENTROID")
point_allocation_sect = arcpy.Intersect_analysis([remainder_to_points, allocation_vector], r"in_memory\point_allocation_sect", "#", "#", "POINT")

#input_dict = utility.get_field_value_as_dict(point_allocation_sect, "PROPERTYID", "gridcode")
#utility.assign_field_value_from_dict_and_set_process_source(input_dict, config.taxlots, "PROPERTYID", "LOCALID", "majority allocation")
utility.get_and_assign_field_value_and_set_process_source(point_allocation_sect,
                                                          "PROPERTYID",
                                                          "gridcode",
                                                          config.taxlots,
                                                          "PROPERTYID",
                                                          "LOCALID",
                                                          "majority allocation")


#print("  ---   ROW to TL sj fields")
#for field in utility.list_field_names(ROW_to_TL_sj_1toM):
#    print(field)

#print("  ----  taxlot fields")
#for field in utility.list_field_names(config.taxlots):
#    print(field)

# REMOVE AFTER QC
#arcpy.CopyFeatures_management(config.taxlots, os.path.join(config.output_gdb, "TL_intermediate_1"))
arcpy.CopyFeatures_management(ROW_to_TL_sj_1toM, os.path.join(config.output_gdb, "ROW_to_TL_sj_1toM_intermediate_1"))

log_obj.info("Create Block Objects - writing to disk".format())
arcpy.CopyFeatures_management(config.taxlots, os.path.join(config.output_gdb, "taxlots_intermediate_TEST"))

log_obj.info("Create Block Objects - done".format())