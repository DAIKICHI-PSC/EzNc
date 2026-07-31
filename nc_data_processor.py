def process_nc_data(raw_bytes):
    transfer_data = ""
    percent_flag = False
    first_percent = False
    comment_flag = False

    for byte_val in raw_bytes:
        dmy = byte_val

        if dmy in (256, 141, 136, 18, 20, 9):
            dmy = 0

        if dmy == 165:
            dmy = 0
            percent_flag = True
            if not first_percent:
                first_percent = True
            else:
                first_percent = False

        if dmy == 10 and percent_flag:
            dmy = 0
            percent_flag = False

        if not first_percent:
            dmy = 0

        if dmy == 40:
            comment_flag = True
        if dmy == 161:
            comment_flag = False

        if dmy == 160 and not comment_flag:
            dmy = 0

        if dmy == 58:
            dmy = 79

        if dmy > 128:
            dmy = dmy - 128

        if dmy > 0:
            transfer_data += chr(dmy)

    return transfer_data


def validate_data_name(name):
    invalid_chars = "\\/:,;\"<>|"
    for ch in invalid_chars:
        if ch in name:
            return False
    return True


def ascii_to_iso(data):
    iso_data = ""
    for ch in data:
        code = ord(ch)
        if code > 0 and code <= 127:
            iso_code = code + 128
            iso_data += chr(iso_code)
        else:
            iso_data += ch
    return iso_data
