def remove_non_english(df, column):

  for i, row in df.iterrows():

    if column=='artists':
      df[column].replace({r'[\[\]\']':""}, regex=True, inplace=True)

    if re.match(r'[^a-zA-Z0-9 &\,]+', artist_list):
        df.loc[i,column] = ''
        df.drop(df[df[column]==''].index, inplace=True)
        df.index = range(len(df.index))

  return df


df_data = pd.read_csv('data.csv')

df_data = remove_non_english(df_data,'artists')

df_data.to_csv('Cleaned data.csv')