"""
This script requires the user to use the script
"TSPerf/energy_load/GEFCom2017-D_Prob_MT_hourly/common/download_data.py" to
download the SMD Hourly Data from 2011 to 2017 from the ISO New England
website (https://www.iso-ne.com/isoexpress/web/reports/load-and-demand/-/tree/zone-info).
The downloaded data is stored in
"TSPerf/energy_load/TSPerf/energy_load/GEFCom2017-D_Prob_MT_hourly/data"

This script parses the excel files and creates training and testing data files.
After running this script, the following files are generated:
data/train/train_base.csv   : 2011-01-01 01:00:00 - 2016-12-01 00:00:00
data/train/train_round_1.csv: 2016-12-01 01:00:00 - 2016-12-15 00:00:00
data/train/train_round_2.csv: 2016-12-01 01:00:00 - 2016-12-31 00:00:00
data/train/train_round_3.csv: 2016-12-01 01:00:00 - 2017-01-15 00:00:00
data/train/train_round_4.csv: 2016-12-01 01:00:00 - 2017-01-31 00:00:00
data/train/train_round_5.csv: 2016-12-01 01:00:00 - 2017-02-14 00:00:00
data/train/train_round_6.csv: 2016-12-01 01:00:00 - 2017-02-28 00:00:00
data/test/test_round_1.csv  : 2017-01-01 01:00:00 - 2017-02-01 00:00:00
data/test/test_round_2.csv  : 2017-02-01 01:00:00 - 2017-03-01 00:00:00
data/test/test_round_3.csv  : 2017-02-01 01:00:00 - 2017-03-01 00:00:00
data/test/test_round_4.csv  : 2017-03-01 01:00:00 - 2017-04-01 00:00:00
data/test/test_round_5.csv  : 2017-03-01 01:00:00 - 2017-04-01 00:00:00
data/test/test_round_6.csv  : 2017-04-01 01:00:00 - 2017-05-01 00:00:00
Concatenating train_base.csv and train_round_n.csv give the training data
of round n. The script serve_folds.py does this automatically.

The output files contain the following columns
Datetime:
    Generated by combining the Date and Hour columns of the excel files.
    Note that 00:00:00 of a particular day corresponds to Hour=24
    of the previous day in the excel files.
DEMAND:
    Real-Time Demand is Non-PTF Demand for wholesale market settlement
    from revenue quality metering, and is defined as the sum of non-dispatchable
    load assets, station service load assets, and unmetered load assets
DryBulb:
    The dry-bulb temperature in °F for the weather station
    corresponding to the load zone or Trading Hub.
DewPnt:
    The dewpoint temperature in °F for the weather station corresponding
    to the load zone or Trading Hub.
Zone:
    The load zone, which corresponds to the sheet names in the excel files.
    In addition to the eight zones in the excel files, 'SEMA', 'WCMA',
    and 'NEMA' are aggregated to generate the MA_TOTAL zone and all eight
    zones are aggregated to generate the TOTAL zone. Therefore, the 'Zone'
    column contains 10 unique values in total. The DEMAND is summed across
    the zones, and the DryBulb and DewPnt are averaged across the zones.
Holiday:
    Ten major US holidays encoded in integers.
    0: Non-holiday
    1: New Year's Day
    2: Birthday of Martin Luther King Jr.
    3: Washington's Birthday
    4: Memorial Day
    5: Independence Day
    6: Labor Day
    7: Columbus Day
    8: Veterans Day
    9: Thanksgiving Day
    10: Christmas Day
"""

import os, sys, getopt, inspect
from datetime import timedelta

import pandas as pd
import numpy as np

# This assumes that the script is stored in a directory of the same level
# as the data directory
SCRIPT_PATH = os.path.dirname(os.path.abspath(inspect.getfile(
    inspect.currentframe())))
DATA_DIR_LEVEL = os.path.dirname(SCRIPT_PATH)
DATA_DIR = os.path.join(DATA_DIR_LEVEL, 'data')
TRAIN_DATA_DIR = DATA_DIR + '/train'
TEST_DATA_DIR = DATA_DIR + '/test'
# This file stores all the data before 2016-12-01
TRAIN_BASE_FILE = 'train_base.csv'
# These files contain data to be added to train_base.csv to form the training
# data of a particular round
TRAIN_ROUND_FILE_PREFIX = 'train_round_'
TEST_ROUND_FILE_PREFIX = 'test_round_'

DATA_FILE_LIST = ['2011_smd_hourly.xls', '2012_smd_hourly.xls',
                  '2013_smd_hourly.xls', '2014_smd_hourly.xls',
                  '2015_smd_hourly.xls', '2016_smd_hourly.xls',
                  '2017_smd_hourly.xlsx']
# These are the files with SHEET_LIST_NEW and COLUMN_LIST_NEW
DATA_FILE_LIST_NEW_FORMAT= ['2016_smd_hourly.xls', '2017_smd_hourly.xlsx']
SHEET_LIST = ['ME', 'NH', 'VT', 'CT', 'RI', 'SEMASS', 'WCMASS', 'NEMASSBOST']
SHEET_LIST_NEW = ['ME', 'NH', 'VT', 'CT', 'RI', 'SEMA', 'WCMA', 'NEMA']
MA_ZONE_LIST = ['SEMA', 'WCMA', 'NEMA']
COLUMN_LIST = ['Date', 'Hour', 'DEMAND', 'DryBulb', 'DewPnt']
COLUMN_LIST_NEW = ['Date', 'Hr_End', 'RT_Demand', 'Dry_Bulb', 'Dew_Point']

TRAIN_BASE_END = pd.to_datetime('2016-12-01')
TRAIN_ROUNDS_ENDS = pd.to_datetime(['2016-12-15', '2016-12-31',
                                    '2017-01-15', '2017-01-31',
                                    '2017-02-14', '2017-02-28'])

TEST_STARTS_ENDS = [pd.to_datetime(('2017-01-01', '2017-02-01')),
                    pd.to_datetime(('2017-02-01', '2017-03-01')),
                    pd.to_datetime(('2017-02-01', '2017-03-01')),
                    pd.to_datetime(('2017-03-01', '2017-04-01')),
                    pd.to_datetime(('2017-03-01', '2017-04-01')),
                    pd.to_datetime(('2017-04-01', '2017-05-01'))]

# These dates are used to correct doubled demand values at the end of DST
# every year. The problem is fixed starting from 2016. It doesn't worth
# doing outlier detection for these 5 data points.
DST_END_DATETIME = pd.to_datetime(['2011-11-06 02:00:00',
                                   '2012-11-04 02:00:00',
                                   '2013-11-03 02:00:00',
                                   '2014-11-02 02:00:00',
                                   '2015-11-01 02:00:00'])
# Holiday data file path
HOLIDAY_DATA_DIR_LEVEL = os.path.dirname(os.path.dirname(os.path.dirname(
    SCRIPT_PATH)))
HOLIDAY_DATA_FILE = \
    os.path.join(HOLIDAY_DATA_DIR_LEVEL, 'common', 'us_holidays.csv')

# Holiday dictionary used to map holidays to integers
HOLIDAY_TO_INT_DICT = {"New Year's Day": 1,
                       "Birthday of Martin Luther King Jr.": 2,
                       "Washington's Birthday": 3,
                       "Memorial Day": 4,
                       "Independence Day": 5,
                       "Labor Day": 6,
                       "Columbus Day": 7,
                       "Veterans Day": 8,
                       "Thanksgiving Day": 9,
                       "Christmas Day": 10}

def check_data_exist(data_dir):
    """
    This function makes sure that all data are downloaded to the data
    directory.
    """

    data_dir_files = os.listdir(data_dir)
    for f in DATA_FILE_LIST:
        if f not in data_dir_files:
            raise Exception('The data file {0} is not found in the data '
                            'directory {1}, make sure you download the data '
                            'as instructed and try again.'.format(f, data_dir))

def parse_excel(file_name):
    """
    This function parses an excel file with multiple sheets and returns a
    panda data frame.
    """
    file_path = os.path.join(DATA_DIR, file_name)
    xls = pd.ExcelFile(file_path)

    if file_name in DATA_FILE_LIST_NEW_FORMAT:
        sheet_list_cur = SHEET_LIST_NEW
    else:
        sheet_list_cur = SHEET_LIST

    df_list = []
    for i in range(len(sheet_list_cur)):
        sheet_name = sheet_list_cur[i]
        print(sheet_name)
        df = pd.read_excel(xls, sheet_name)
        if file_name in DATA_FILE_LIST_NEW_FORMAT:
            df = df[COLUMN_LIST_NEW]
            # make sure column names are unified
            df.columns = COLUMN_LIST
        else:
            df = df[COLUMN_LIST]

        # make sure zone names are unified
        df['Zone'] = SHEET_LIST_NEW[i]

        # combine date and hour column to get timestamp
        df['Datetime'] = df.apply(
            lambda row: row.Date + timedelta(hours=row.Hour), axis=1)
        df.drop(['Date', 'Hour'], axis=1, inplace=True)

        df_list.append(df)

    df_eight_zones = pd.concat(df_list)
    df_eight_zones.reset_index(inplace=True, drop=True)

    # Create aggregated data for Massachusetts. For each timestamp, sum the
    # demand, average the DryBulb temperature, and average the DewPnt
    # temperature for all three zones.
    df_MA_zones = df_eight_zones.loc[df_eight_zones['Zone'].isin(MA_ZONE_LIST)]
    df_MA = df_MA_zones[['DEMAND', 'Datetime']].groupby('Datetime').sum()
    df_MA['DryBulb'] = \
        round(df_MA_zones[['DryBulb', 'Datetime']].groupby('Datetime').mean())
    df_MA['DryBulb'] = df_MA['DryBulb'].astype(int)
    df_MA['DewPnt'] =  \
        round(df_MA_zones[['DewPnt', 'Datetime']].groupby('Datetime').mean())
    df_MA['DewPnt'] = df_MA['DewPnt'].astype(int)
    df_MA['Zone'] = 'MA_TOTAL'

    df_MA.reset_index(inplace=True)

    # Create aggregated data for all eight zones. For each timestamp, sum the
    # demand, average the DryBulb temperature, and average the DewPnt
    # temperature for all eight zones.
    df_total = df_eight_zones[['DEMAND', 'Datetime']].groupby('Datetime').sum()
    df_total['DryBulb'] = \
        round(df_eight_zones[['DryBulb', 'Datetime']].groupby('Datetime').mean())
    df_total['DryBulb'] = df_total['DryBulb'].astype(int)
    df_total['DewPnt'] =  \
        round(df_eight_zones[['DewPnt', 'Datetime']].groupby('Datetime').mean())
    df_total['DewPnt'] = df_total['DewPnt'].astype(int)
    df_total['Zone'] = 'TOTAL'

    df_total.reset_index(inplace=True)

    df_final = pd.concat([df_eight_zones, df_MA, df_total], sort=True)
    df_final.reset_index(inplace=True, drop=True)

    return df_final

def preprocess_holiday_data():
    holidays = pd.read_csv(HOLIDAY_DATA_FILE)
    holidays['Date'] = pd.to_datetime(holidays['Date'])
    # Map holiday names to integers
    holidays = holidays.replace({'Holiday': HOLIDAY_TO_INT_DICT})
    # Create a holiday record for each hour
    hours = pd.DataFrame({'hour': list(range(1, 25))})
    holidays['key'] = 1
    hours['key'] = 1
    holidays_with_hours = pd.merge(holidays, hours, on='key')
    holidays_with_hours['Datetime'] = holidays_with_hours.apply(
        lambda row: row.Date + timedelta(hours=row.hour), axis=1)
    holidays_with_hours.drop(['Date', 'hour', 'key'], axis=1, inplace=True)

    holidays_with_hours.set_index('Datetime', inplace=True)

    return holidays_with_hours

def merge_with_holiday_data(input_df, holiday_df):
    output_df = pd.merge(input_df, holiday_df, how='left', left_index=True,
                         right_index=True)
    output_df.fillna(value=0, inplace=True)
    output_df['Holiday'] = output_df['Holiday'].astype(int)

    return output_df

def main(preprocess_flag):
    """
    :param preprocess_flag: A boolean flag that determines whether data '
          'preprocessing should be applied to the extracted data. If True, '
          'zero values will be filled by linearly interpolation, outliers '
          'caused by end of Daylight Saving Time will be divided by 2. '
          'Default: True.'
    :type preprocess_flag: bool
    """
    # Make sure all files are downloaded to the data directory
    check_data_exist(DATA_DIR)

    # preprocess the holiday data
    holiday_df = preprocess_holiday_data()

    # Create train and test data directories
    if not os.path.isdir(TRAIN_DATA_DIR):
        os.mkdir(TRAIN_DATA_DIR)

    if not os.path.isdir(TEST_DATA_DIR):
        os.mkdir(TEST_DATA_DIR)

    file_df_list = []
    for file_name in DATA_FILE_LIST:
        print(file_name)
        file_df = parse_excel(file_name)
        file_df_list.append(file_df)

    file_df_final = pd.concat(file_df_list)
    file_df_final.sort_values(['Zone', 'Datetime'])
    file_df_final.reset_index(inplace=True, drop=True)

    if preprocess_flag:
        # Fill zero values at the beginning of DST using the demand
        # of the same hour of yesterday
        zero_indices = file_df_final[file_df_final['DEMAND']==0].index.values
        lag_24_indices = zero_indices - 24

        file_df_final.loc[zero_indices, 'DEMAND'] = \
            file_df_final.loc[lag_24_indices, 'DEMAND'].values

        # Divide outliers at the end of DST by 2
        dst_end_datetime_mask = \
            file_df_final['Datetime'].isin(DST_END_DATETIME)
        file_df_final.loc[dst_end_datetime_mask,'DEMAND'] = \
            round(file_df_final.loc[dst_end_datetime_mask,'DEMAND']/2)

    file_df_final.set_index('Datetime', inplace=True)
    file_df_final = merge_with_holiday_data(file_df_final, holiday_df)

    index_value = file_df_final.index.get_level_values(0)
    train_base_df = file_df_final.loc[index_value <= TRAIN_BASE_END]
    train_base_df.to_csv(os.path.join(TRAIN_DATA_DIR, TRAIN_BASE_FILE))
    print('Base training data frame size: {}'.format(train_base_df.shape))

    for i in range(len(TRAIN_ROUNDS_ENDS)):
        file_name = os.path.join(TRAIN_DATA_DIR,
                                 TRAIN_ROUND_FILE_PREFIX + str(i+1) + '.csv')
        train_round_delta_df = file_df_final.loc[
            (index_value > TRAIN_BASE_END)
            & (index_value <= TRAIN_ROUNDS_ENDS[i])]
        print('Round {0} additional training data size: {1}'.format(i+1,
            train_round_delta_df.shape))
        print('Minimum timestamp: {0}'
              .format(min(train_round_delta_df.index.get_level_values(0))))
        print('Maximum timestamp: {0}'
              .format(max(train_round_delta_df.index.get_level_values(0))))
        print('')
        train_round_delta_df.to_csv(file_name)

    for i in range(len(TEST_STARTS_ENDS)):
        file_name = os.path.join(TEST_DATA_DIR,
                                 TEST_ROUND_FILE_PREFIX + str(i+1) + '.csv')
        start_end = TEST_STARTS_ENDS[i]
        test_round_df = file_df_final.loc[
            ((index_value > start_end[0]) & (index_value <= start_end[1]))
        ]
        print('Round {0} testing data size: {1}'
              .format(i+1, test_round_df.shape))
        print('Minimum timestamp: {0}'
        .format(min(test_round_df.index.get_level_values(0))))
        print('Maximum timestamp: {0}'
        .format(max(test_round_df.index.get_level_values(0))))
        print('')
        test_round_df.to_csv(file_name)

def usage():
    print('usage: python extract_data.py [--preprocess]\n'
          'Options and arguments:\n'
          '--preprocess: A boolean flag that determines whether data '
          'preprocessing should be applied to the extracted data.\n'
          '              If True, zero values will be filled by the '
          'values of the same hour of the previous day, outliers caused by '
          'end of Daylight Saving Time will be divided by 2.\n'
          '              Default: True.')

if __name__ == '__main__':
    preprocess_flag = True
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'h', ['help', 'preprocess='])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '--preprocess':
            if arg in ('True', 'T'):
                preprocess_flag = True
            elif arg in ('False', 'F'):
                preprocess_flag = False
            else:
                raise Exception('Invalid value for option "--preprocess": {0}. Valid values are True or T, False or F'.format(arg))
        elif opt in ("-h", "--help"):
            usage()
            sys.exit()

    main(preprocess_flag)