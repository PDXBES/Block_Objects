import config
import utility
import arcpy
import os

log_obj = utility.Logger(config.log_file)
log_obj.info("Block Object Population Estimate - starting".format())

log_obj.info("Block Object Population Estimate - taxlots to points".format())
TL_points = arcpy.FeatureToPoint_management(config.RES_cayenta_taxlots, r"in_memory\TL_points")

log_obj.info("Block Object Population Estimate - intersect taxlot points and census blocks".format())
TL_points_CB_sect = arcpy.Intersect_analysis([TL_points, config.census_blocks_2020], r"in_memory\TL_points_CB_sect", "", "", "point")

log_obj.info("Block Object Population Estimate - summary stats on result of intersect".format())
CB_sums = arcpy.analysis.Statistics(TL_points_CB_sect, r"in_memory\CB_sums", [["gal_per_day", "SUM"], ["Pop", "FIRST"]], "FIPS_BLOCK")

log_obj.info("Block Object Population Estimate - calc gal per day per person".format())
utility.add_numeric_field(CB_sums, "gal_per_day_per_person", "DOUBLE")
with arcpy.da.UpdateCursor(CB_sums, ["SUM_gal_per_day", "FIRST_Pop", "gal_per_day_per_person"]) as cursor:
    for row in cursor:
        if row[0] is not None and row[1] is not None:
            if row[1] != 0:
                row[2] = row[0]/row[1]
            else:
                row[2] = 0
            cursor.updateRow(row)

log_obj.info("Block Object Population Estimate - join sums result back to intersect".format())
arcpy.JoinField_management(TL_points_CB_sect, "FIPS_BLOCK", CB_sums, "FIPS_BLOCK", "gal_per_day_per_person")

log_obj.info("Block Object Population Estimate - calc taxlot population".format())
utility.add_numeric_field(TL_points_CB_sect, "TL_Pop", "DOUBLE")
with arcpy.da.UpdateCursor(TL_points_CB_sect, ["gal_per_day", "gal_per_day_per_person", "TL_Pop"]) as cursor:
    for row in cursor:
        if row[0] is not None and row[1] is not None:
            if row[1] != 0:
                row[2] = row[0]/row[1]
            else:
                row[2] = 0
            cursor.updateRow(row)

log_obj.info("Block Object Population Estimate - intersect result with block objects".format())
TL_points_BO_sect = arcpy.Intersect_analysis([TL_points_CB_sect, config.block_objects], r"in_memory\TL_points_BO_sect", "", "", "point")

#print(utility.list_field_names(TL_points_BO_sect))

log_obj.info("Block Object Population Estimate - sum population per block object".format())
BO_pop_sums = arcpy.analysis.Statistics(TL_points_BO_sect, r"in_memory\BO_pop_sums", [["TL_Pop", "SUM"]], "FINAL_ID")

#print(utility.list_field_names(BO_pop_sums))

log_obj.info("Block Object Population Estimate - join sums result to block objects".format())
arcpy.JoinField_management(config.block_objects, "FINAL_ID", BO_pop_sums, "FINAL_ID", "SUM_TL_Pop")

output_fc = os.path.join(config.output_gdb, "block_object_EstPop")
log_obj.info("Block Object Population Estimate - saving output to - {}".format(output_fc))
arcpy.CopyFeatures_management(config.block_objects, output_fc)

log_obj.info("Block Object Population Estimate - complete".format())