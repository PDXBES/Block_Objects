import arcpy
import utility
import os
from datetime import datetime

print("Starting Config: " + datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))

log_file = r"\\besfile1\ism_projects\Work_Orders\Joes_Sandbox\dev\block_objects_log"
output_gdb = r"\\besfile1\ASM_AssetMgmt\Projects\Interagency Risk Grid\BlockEval\Data\Arc\GDB\block_automation.gdb"

CCF_to_gal_per_day = 748
days_per_year = 365

connections = r"\\besfile1\grp117\DAshney\Scripts\connections"

BESGEORPT_TEST = os.path.join(connections, "BESDBTEST1.BESGEORPT.OSA.sde")
EGH_PUBLIC = os.path.join(connections, "egh_public on gisdb1.rose.portland.local.sde")
BESDBPROD1 = os.path.join(connections, "BESDBPROD1.SWSP.sde")

block_objects_raw = r"\\besfile1\ASM_AssetMgmt\Projects\Interagency Risk Grid\BlockEval\Data\Arc\GDB\block_working_v2.gdb\block_objects"
census_blocks_2020_raw = r"\\Besfile1\ISM_projects\Work_Orders\WO_9981_J_Hoffman\Shp\Census_2020_Blocks.shp"
city_boundary_raw = EGH_PUBLIC + r"\EGH_Public.ARCMAP_ADMIN.portland_pdx"
taxlots_raw = EGH_PUBLIC + r"\EGH_Public.ARCMAP_ADMIN.taxlots_pdx"
street_centerline_raw = EGH_PUBLIC + r"\EGH_Public.ARCMAP_ADMIN.streets_pdx"
ARC_ROW_raw = BESDBPROD1 + r"\SWSP.GIS.ARC_ROW"
#print(arcpy.GetCount_management(ARC_ROW_raw))

# create feature layers and subset by attributes if needed
taxlots_FL = arcpy.MakeFeatureLayer_management(taxlots_raw, r"in_memory\taxlots_FL")
taxlots_sub = arcpy.MakeFeatureLayer_management(taxlots_raw, r"in_memory\taxlots_sub", "YEARBUILT is not Null AND YEARBUILT not in ( '0' , '' , '9999')")
street_centerline_FL = arcpy.MakeFeatureLayer_management(street_centerline_raw, r"in_memory\street_centerline_FL")
ARC_ROW_FL = arcpy.MakeFeatureLayer_management(ARC_ROW_raw, r"in_memory\ARC_ROW_FL", "Id is not Null")
#print(arcpy.GetCount_management(ARC_ROW_sub))

# subset by geographic area
arcpy.SelectLayerByLocation_management(taxlots_FL, "HAVE_THEIR_CENTER_IN", city_boundary_raw)
arcpy.SelectLayerByLocation_management(street_centerline_FL, "HAVE_THEIR_CENTER_IN", city_boundary_raw)
arcpy.SelectLayerByLocation_management(ARC_ROW_FL, "HAVE_THEIR_CENTER_IN", city_boundary_raw)
arcpy.SelectLayerByLocation_management(taxlots_sub, "HAVE_THEIR_CENTER_IN", city_boundary_raw)
#print(arcpy.GetCount_management(ARC_ROW_sub))

# this is based on a view which is based on copies of CU and the taxlots - should move/ point at live
RES_cayenta_taxlots_QL = arcpy.MakeQueryLayer_management(BESGEORPT_TEST,
                                                  "RES_cayenta_taxlots_QL",
                                                  "SELECT * from BESGEORPT.GIS.v_CU_taxlots where "
                                                  "WATER_SERVICE = 'WATER' and "
                                                  "LOCATION_CLASS in ( 'RESMF' , 'RESSF' )",
                                                  "LOCATION_NO")

# copy all into memory
block_objects = arcpy.CopyFeatures_management(block_objects_raw, r"in_memory\block_objects")
census_blocks_2020 = arcpy.CopyFeatures_management(census_blocks_2020_raw, r"in_memory\census_blocks_2020")
RES_cayenta_taxlots = arcpy.CopyFeatures_management(RES_cayenta_taxlots_QL, r"in_memory\RES_cayenta_taxlots")
taxlots = arcpy.CopyFeatures_management(taxlots_FL, r"in_memory\taxlots")
taxlots_yearbuilt = arcpy.CopyFeatures_management(taxlots_sub, r"in_memory\taxlots_yearbuilt")
street_centerlines = arcpy.CopyFeatures_management(street_centerline_FL, r"in_memory\street_centerlines")
ARC_ROW = arcpy.CopyFeatures_management(ARC_ROW_FL, r"in_memory\ARC_ROW")
#print(arcpy.GetCount_management(ARC_ROW))

utility.add_field_if_needed(RES_cayenta_taxlots, "gal_per_day", "DOUBLE")
with arcpy.da.UpdateCursor(RES_cayenta_taxlots, ["gal_per_day", "WINTER_AVERAGE_AMOUNT"]) as cursor:
    for row in cursor:
        if row[1] is not None:
            row[0] = row[1]*(CCF_to_gal_per_day/days_per_year)
            cursor.updateRow(row)

utility.add_field_if_needed(census_blocks_2020, "Pop", "LONG")
with arcpy.da.UpdateCursor(census_blocks_2020, ["Pop_sqmi", "SQMI", "Pop"]) as cursor:
    for row in cursor:
        if row[0] is not None and row[1] is not None:
            row[2] = row[0] * row[1]
            cursor.updateRow(row)

utility.add_field_if_needed(taxlots_yearbuilt, "YEARBUILT_int", "SHORT")
with arcpy.da.UpdateCursor(taxlots_yearbuilt, ["YEARBUILT", "YEARBUILT_int"]) as cursor:
    for row in cursor:
        if row[0] is not None:
            row[1] = int(row[0])
            cursor.updateRow(row)

utility.add_field_if_needed(taxlots, "process_source", "TEXT", length=25)
utility.add_field_if_needed(taxlots, "LOCALID", "LONG")


print("Config Complete: " + datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))