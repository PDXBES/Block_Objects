import config
import utility
import arcpy
import os

log_obj = utility.Logger(config.log_file)
log_obj.info("Block Object Population Estimate - starting".format())

