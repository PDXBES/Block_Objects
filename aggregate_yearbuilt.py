import config
import utility
import os
import arcpy

block_objects = os.path.join(config.output_gdb, "block_objects")
block_objects_copy = arcpy.CopyFeatures_management(block_objects, r"in_memory\block_objects_copy")


log_obj = utility.Logger(config.log_file)
log_obj.info("Create aggregate yearbuilt - Starting".format())

log_obj.info("Create aggregate yearbuilt - converting taxlots to point".format())
taxlots_to_points = arcpy.FeatureToPoint_management(config.taxlots_yearbuilt, r"in_memory\taxlots_to_points", "CENTROID")

log_obj.info("Create aggregate yearbuilt - intersecting points with block objects".format())
TL_points_BO_sect = arcpy.Intersect_analysis([taxlots_to_points, block_objects_copy], r"in_memory\TL_points_BO_sect", "#", "#", "POINT")

log_obj.info("Create aggregate yearbuilt - running summary stats (mean yearbuilt)".format())
sect_stats = arcpy.analysis.Statistics(TL_points_BO_sect, r"in_memory\sect_stats", [["YEARBUILT_int", "MEAN"]], "block_object_ID")

log_obj.info("Create aggregate yearbuilt - adding/ populating block object mean yearbuilt".format())
utility.add_field_if_needed(block_objects_copy, "MEAN_YEARBUILT", "SHORT")
utility.add_field_if_needed(block_objects_copy, "process_source", "TEXT", length=25)
utility.get_and_assign_field_value_and_set_process_source(sect_stats,
                                                          "block_object_ID",
                                                          "MEAN_YEARBUILT_int",
                                                          block_objects_copy,
                                                          "block_object_ID",
                                                          "MEAN_YEARBUILT",
                                                          "taxlot_mean")

log_obj.info("Create aggregate yearbuilt - intersecting remaining block objects with adjacent taxlots".format())
BO_remaining = arcpy.MakeFeatureLayer_management(block_objects_copy, r"in_memory\BO_remaining", "MEAN_YEARBUILT is Null")
print(arcpy.GetCount_management(block_objects_copy))
print(arcpy.GetCount_management(BO_remaining))
BO_remaining_buff5ft = arcpy.Buffer_analysis(BO_remaining, r"in_memory\BO_remaining_buff5ft", 5)
remaining_sect = arcpy.Intersect_analysis([BO_remaining_buff5ft, config.taxlots_yearbuilt], r"in_memory\remaining_sect")

log_obj.info("Create aggregate yearbuilt - running summary stats (mean yearbuilt) from adjacent lots".format())
sect_stats_remaining = arcpy.analysis.Statistics(remaining_sect, r"in_memory\sect_stats_remaining", [["YEARBUILT_int", "MEAN"]], "block_object_ID")

log_obj.info("Create aggregate yearbuilt - adding/ populating remaining block objects mean yearbuilt".format())
utility.get_and_assign_field_value_and_set_process_source(sect_stats_remaining,
                                                          "block_object_ID",
                                                          "MEAN_YEARBUILT_int",
                                                          block_objects_copy,
                                                          "block_object_ID",
                                                          "MEAN_YEARBUILT",
                                                          "adjacent_mean")

log_obj.info("Create Block Objects - writing to disk".format())
arcpy.CopyFeatures_management(block_objects_copy, os.path.join(config.output_gdb, "block_objects_agg_yearbuilt"))
print(utility.list_field_names(block_objects_copy))

log_obj.info("Create aggregate yearbuilt - Done".format())