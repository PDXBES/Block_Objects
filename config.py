import arcpy
import os

log_file = r"\\besfile1\ism_projects\Work_Orders\Joes_Sandbox\dev\block_objects_log.log"

connections = r"\\besfile1\grp117\DAshney\Scripts\connections"

BESGEORPT_TEST = os.path.join(connections, "BESDBTEST1.BESGEORPT.OSA.sde")

block_objects = r"\\besfile1\ASM_AssetMgmt\Projects\Interagency Risk Grid\BlockEval\Data\Arc\GDB\block_working_v2.gdb\block_objects"
census_blocks_2020 = r"\\Besfile1\ISM_projects\Work_Orders\WO_9981_J_Hoffman\Shp\Census_2020_Blocks.shp"

# this is based on a view which is based on copies of CU and the taxlots - should move/ point at live
RES_cayenta_taxlots = arcpy.MakeQueryLayer_management(BESGEORPT_TEST,
                                                  "RES_cayenta_taxlots",
                                                  "SELECT * from BESGEORPT.GIS.v_CU_taxlots where "
                                                  "WATER_SERVICE = 'WATER' and "
                                                  "LOCATION_CLASS in ( 'RESMF' , 'RESSF' )",
                                                  "LOCATION_NO")

