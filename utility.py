import logging
import logging.config
import sys
import arcpy


# https://stackoverflow.com/questions/6386698/how-to-write-to-a-file-using-the-logging-python-module
def Logger(file_name):
    formatter = logging.Formatter(fmt='%(asctime)s %(module)s,line: %(lineno)d %(levelname)8s | %(message)s',
                                  datefmt='%Y/%m/%d %H:%M:%S')  # %I:%M:%S %p AM|PM format
    logging.basicConfig(filename='%s.log' % (file_name),
                        format='%(asctime)s %(module)s,line: %(lineno)d %(levelname)8s | %(message)s',
                        datefmt='%Y/%m/%d %H:%M:%S', filemode='a', level=logging.INFO)
    log_obj = logging.getLogger()
    log_obj.setLevel(logging.DEBUG)
    # log_obj = logging.getLogger().addHandler(logging.StreamHandler())

    # console printer
    screen_handler = logging.StreamHandler(stream=sys.stdout)  # stream=sys.stdout is similar to normal print
    screen_handler.setFormatter(formatter)
    logging.getLogger().addHandler(screen_handler)

    log_obj.info("Starting log session..")
    return log_obj


def list_field_names(input_fc):
    field_names = []
    fields = arcpy.ListFields(input_fc)
    for field in fields:
        field_names.append(field.name)
    return field_names


def add_numeric_field(input_fc, field_name, field_type):
    if field_name not in list_field_names(input_fc):
        arcpy.AddField_management(input_fc, field_name, field_type)


def add_field_if_needed(input_fc, field_to_add, field_type, scale = None, length = None):
    field_names = list_field_names(input_fc)
    if field_to_add not in field_names:
        arcpy.AddField_management(input_fc, field_to_add, field_type, scale, length)


def delete_fields(existing_table, keep_fields_list):
    field_name_required_dict = get_field_names_and_required(existing_table)
    remove_list = create_remove_list(field_name_required_dict, keep_fields_list)
    arcpy.DeleteField_management(existing_table, remove_list)


def get_field_names_and_required(input):
    name_and_required_dict = {}
    fields = arcpy.ListFields(input)
    for field in fields:
        name_and_required_dict[field.name] = field.required
    return name_and_required_dict


def create_remove_list(existing_names_and_required, field_list):
    remove_field_list = []
    for key, value in existing_names_and_required.items():
        # second param tests for required fields (OID, Shape, etc), don't want to include these as we cannot modify them
        if key not in field_list and key not in ('Shape', 'OBJECTID') and value != True:
            remove_field_list.append(key)
    return remove_field_list


def get_field_value_as_dict(input, key_field, value_field):
    value_dict = {}
    with arcpy.da.SearchCursor(input, (key_field, value_field)) as cursor:
        for row in cursor:
            value_dict[row[0]] = row[1]
    return value_dict


def assign_field_value_from_dict(input_dict, target, target_key_field, target_field):
    with arcpy.da.UpdateCursor(target, (target_key_field, target_field)) as cursor:
        for row in cursor:
            for key, value in input_dict.items():
                if row[0] == key:
                    row[1] = value
            cursor.updateRow(row)


#def assign_field_value_from_dict_and_set_process_source(input_dict, target, target_key_field, target_field, process_source_value):
#    with arcpy.da.UpdateCursor(target, (target_key_field, target_field, "process_source")) as cursor:
#        for row in cursor:
#            for key, value in input_dict.items():
#                if row[0] == key:
#                    row[1] = value
#                    row[2] = process_source_value
#            cursor.updateRow(row)

def assign_field_value_from_dict_and_set_process_source(input_dict, target, target_key_field, target_field, process_source_value):
    with arcpy.da.UpdateCursor(target, (target_key_field, target_field, "process_source")) as cursor:
        for row in cursor:
            if row[0] in input_dict.keys():
                row[1] = input_dict[row[0]]
                row[2] = process_source_value
            cursor.updateRow(row)


def get_and_assign_field_value_and_set_process_source(source, source_key_field, source_field, target, target_key_field, target_field, process_source_value):
    value_dict = get_field_value_as_dict(source, source_key_field, source_field)
    assign_field_value_from_dict_and_set_process_source(value_dict, target, target_key_field, target_field, process_source_value)
