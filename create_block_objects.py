import arcpy.management

import config
import utility

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


# assign ROW to lots (first pass)



("Create Block Objects - done".format())