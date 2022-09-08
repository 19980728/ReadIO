import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib


#関数の準備　ーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーー
#利用方法
def how_to_use():
    st.markdown(
    """
    #### 本アプリの利用方法

    ーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーー

    まずは左サイドバー「↓選択」から利用内容を選択

    ＞

    （「駐車場利用分析」を選択した場合）
    
    ①入出庫データのexcelファイルをアップロード

    ・左枠内にドラッグ＆ドロップ、または枠内をクリック→ファイルを選択

    ・excelファイルには「入庫日時」「出庫日時」「課金額」の列を含むこと！

    ②左サイドバー「事業地名」「駐車可能台数」を入力、必要な場合は期間、課金額による絞り込みも行う

    ③左サイドバー「Menu」からしたいことを選択

    ＞

    （「コロナ感染者推移」を選択した場合）

    ①下記リンクから厚生労働省のオープンデータライブラリにアクセス

    ・リンク　→　https://www.mhlw.go.jp/stf/covid-19/open-data.html

    ②「新規陽性者数の推移（日別）」をクリックしダウンロード

    ③「ダウンロードしたコロナ感染者数データをアップロード」に②でダウンロードしたデータをドラッグ＆ドロップ

    ④左サイドバーから期間、都市名を選択

    ーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーー
    """
    )

#駐車場利用分析
#各種分析用のdf作成
def make_df(file_path):
    df = pd.read_excel(file_path)
    df = pd.DataFrame(data = [ df['入庫日時'].dt.strftime('%Y-%m-%d %H:%M'),
                               df['出庫日時'].dt.strftime('%Y-%m-%d %H:%M'),
                               df['出庫日時'] - df['入庫日時'],
                               df['課金額'] ],
                      index = ['入庫日時','出庫日時','滞在時間','課金額'] ).T
    df['入庫日時'] = pd.to_datetime(df['入庫日時'])
    df['出庫日時'] = pd.to_datetime(df['出庫日時'])
    df['滞在時間'] = pd.to_datetime(df['滞在時間']).dt.strftime('%H:%M')
    df['滞在時間（分）'] = 60 * pd.to_datetime(df['滞在時間']).dt.hour + pd.to_datetime(df['滞在時間']).dt.minute

    for N in ['入庫','出庫']:
        df[f'{N}曜日'] = df[f'{N}日時'].dt.day_name()
        df[f'{N}日'] = df[f'{N}日時'].dt.date
        df[f'{N}時間帯'] = df[f'{N}日時'].dt.hour
        df[f'{N}分'] = df[f'{N}日時'].dt.minute

    df['曜日跨ぎ'] = [0 for i in range(len(df.index))]
    for i,row in df.iterrows():  #入出庫が共に平日:row['曜日跨ぎ']=0,入出庫が共に土日:row['曜日跨ぎ']=2,入出庫が平日+土日:row['曜日跨ぎ']=1
        if row['入庫曜日'] in ['Saturday','Sunday']:
            df['曜日跨ぎ'][i] += 1
        if row['出庫曜日'] in ['Saturday','Sunday']:
            df['曜日跨ぎ'][i] += 1
        df['曜日跨ぎ'][i] = df['曜日跨ぎ'][i] % 2

    return df

#月毎の稼働率推移グラフ描画用
def plt_occupancy_trans(df,capacity):
    #dataframe準備
    dataframe = df.resample('M',on='入庫日時').sum().reset_index()
    dataframe['平均稼働率（％）'] = 100 * dataframe['滞在時間（分）'] / (capacity * 60 * 24 * dataframe['入庫日時'].dt.day)
    dataframe['月'] = dataframe['入庫日時'].dt.strftime('%Y-%m')
    dataframe = dataframe.loc[:,['月','平均稼働率（％）']].set_index('月')

    #グラフ描画
    plt.rcParams['font.size'] = 6
    plt.rcParams['figure.subplot.bottom'] = 0.20
    fig,ax = plt.subplots(figsize=(7,3))
    ax.plot(dataframe.index,dataframe['平均稼働率（％）'],color='red',marker='.')
    ax.set_ylabel('％',rotation='horizontal')
    ax.set_title( f'月ごとの稼働率推移（{dataframe.index.values[0]}〜{dataframe.index.values[-1]}）' )
    ax.grid()
    ax.legend()
    ax.set_xticks(dataframe.index)
    plt.xticks(rotation=45)
    ax.set_yticks([10*i for i in range(10)])

    return dataframe.T,fig

#稼働率計算→稼働率グラフ描画用
def plt_occupancy_rate(df,capacity):
    #dataframe準備
    all = [ 0 for i in range(24) ] #0~23時台の総滞在時間をカウントするためのリスト
    weekdays = [ 0 for i in range(24) ]
    weekend = [ 0 for i in range(24) ]

    for i,row in df.iterrows():
        def distribution(i,add_value):  #平日リストと土日リストに振り分けるための関数 #i番目の要素にadd_valueを加算
            if row['入庫曜日'] in ['Saturday','Sunday']:
                weekend[i] += add_value
            else:
                weekdays[i] += add_value
        
        def distribution_anti(i,add_value):  #曜日を跨いだ後に使用する関数、入庫曜日と違う方のリストに加算
            if row['入庫曜日'] in ['Saturday','Sunday']:
                weekdays[i] += add_value
            else:
                weekend[i] += add_value

        if row['曜日跨ぎ'] == 0:  #曜日跨ぎなし
            if row['入庫時間帯'] == row['出庫時間帯']:
                all[ row['入庫時間帯'] ] += row['滞在時間（分）']
                distribution(i=row['入庫時間帯'],add_value=row['滞在時間（分）'])
            else:
                h = row['入庫時間帯']
                while h != row['出庫時間帯']:
                    if h == row['入庫時間帯']:
                        all[h] += 60 - row['入庫分']
                        distribution(i=h,add_value=60-row['入庫分'])
                    else:
                        all[h] += 60
                        distribution(i=h,add_value=60)
                    h = (h + 1) % 24
                else:
                    all[h] += row['出庫分']
                    distribution(i=h,add_value=row['出庫分'])

        else:  #曜日跨ぎあり
            h = row['入庫時間帯']
            while h%24 != row['出庫時間帯']:
                if h == row['入庫時間帯']:
                    all[h] += 60 - row['入庫分']
                    distribution(i=h,add_value=60-row['入庫分'])
                elif h < 24:
                    all[h%24] += 60
                    distribution(i=h%24,add_value=60)
                else:
                    all[h%24] += 60
                    distribution_anti(i=h%24,add_value=60)
                h = (h + 1)
            else:
                all[h%24] += row['出庫分']
                distribution_anti(i=h%24,add_value=row['出庫分'])

    n = df['入庫日'].nunique()
    n_weekend = df.query('出庫曜日 in ["Saturday","Sunday"]')['入庫日'].nunique()
    n_weekdays = n - n_weekend

    all = [ 100 * c / (60 * capacity * n) for c in all ]

    if n_weekdays == 0:
        weekdays = [0 for i in range(len(weekdays))]
    else:
        weekdays = [ 100 * c / (60 * capacity * n_weekdays) for c in weekdays ]

    if n_weekend == 0:
        weekend = [0 for i in range(len(weekend))]
    else:
        weekend = [ 100 * c / (60 * capacity * n_weekend) for c in weekend ]

    dataframe = pd.DataFrame(data = [all,weekdays,weekend ],index = ['全日稼働率（％）','月〜金稼働率（％）','土日稼働率（％）']).T

    #グラフ描画
    plt.rcParams['font.size'] = 6
    fig,ax = plt.subplots(figsize=(7,3))
    for label,color in zip(['全日','月〜金','土日'],['red','blue','green']):
        ax.plot(dataframe.index,dataframe[f'{label}稼働率（％）'],label=label,color=color,marker='.')
    ax.set_xlabel('時台')
    ax.set_ylabel('％',rotation='horizontal')
    ax.set_title( f"時間帯ごとの稼働率（{df.iat[0,6]}〜{df.iat[-1,6]}）" )
    ax.grid()
    ax.legend()
    ax.set_xticks([i for i in range(24)])
    ax.set_yticks([10*i for i in range(10)])

    return dataframe.T,fig

#平均滞在時間グラフ描画用
def plt_stay_bar(df):
    #dataframe準備
    how_many = [0 for i in range(24)]
    how_long = [0 for i in range(24)]
    for i,row in df.iterrows():
        how_many[row['入庫時間帯']] += 1
        how_long[row['入庫時間帯']] += row['滞在時間（分）']
    count = [m/len(df.index) for m in how_many]
    mean = []
    for m,l in zip(how_many,how_long):
        if m == 0:
            mean.append(0)
        else:
            mean.append(l/m)
    dataframe = pd.DataFrame(data=[count,mean],index=['平均入庫台数（台）','平均滞在時間（分）']).T

    #グラフ描画
    plt.rcParams['font.size'] = 6
    fig,ax1 = plt.subplots(figsize=(7,3))
    ax2 = ax1.twinx()
    ax1.plot(dataframe.index,dataframe['平均入庫台数（台）'],color='blue',marker='.')
    ax2.bar(dataframe.index,dataframe['平均滞在時間（分）'],tick_label=dataframe.index,color='red',alpha=0.4)
    ax1.set_xlabel('時台')
    ax1.set_ylabel('平均入庫台数（台）')
    ax2.set_ylabel('平均滞在時間（分）')
    ax2.spines['left'].set_color('blue')
    ax2.spines['right'].set_color('red')
    ax1.tick_params(axis='y', colors='blue')
    ax2.tick_params(axis='y', colors='red')
    ax1.set_title( f'入庫時間帯ごとの利用分析（{df.iat[0,6]}〜{df.iat[-1,6]}）' )
    
    return dataframe.T,fig

#滞在時間グラフ描画用
def plt_stay_pie(df):
    #dataframe準備
    labels = []
    rate = []
    for i in range(6):
        labels.append(f'〜{10*(i+1)}分')
        rate.append( len( df[ (df['滞在時間（分）'] >= 10*i) & (df['滞在時間（分）'] < 10*(i+1)) ] ) )
    for i in range(1,6):
        labels.append(f'〜{i+1}時間')
        rate.append( len( df[ (df['滞在時間（分）'] >= 60*i) & (df['滞在時間（分）'] < 60*(i+1)) ] ) )
    labels.append('〜12時間')
    rate.append( len( df[ (df['滞在時間（分）'] >= 60*6) & (df['滞在時間（分）'] < 60*12) ] ) )
    labels.append('〜24時間')
    rate.append( len( df[ (df['滞在時間（分）'] >= 60*12) & (df['滞在時間（分）'] < 60*24) ] ) )
    labels.append('24時間〜')
    rate.append( len( df[ df['滞在時間（分）'] >= 60*24 ] ) )
    dataframe = pd.DataFrame(data=[100*r/len(df) for r in rate],index=labels,columns=['割合（％）']).T

    #グラフ描画
    plt.rcParams['font.size'] = 6
    fig,ax = plt.subplots(figsize=(2,2))
    ax.pie(x=rate,  #データ
           labels=labels,  #ラベル
           radius=0.8,  #円の半径
           counterclock=False,  #時計回り
           startangle=90, #開始角度90度
           textprops={'size':'xx-small'},
           labeldistance=None)  #ラベルをグラフ上に表示しない
    ax.set_title( f'滞在時間割合（{df.iat[0,6]}〜{df.iat[-1,6]}）' ,fontsize='xx-small')
    ax.legend(loc=[0,0],fontsize='xx-small')

    return dataframe,fig

#簡易利用分析結果表示用
def show_data(i,df,fig,date_from,date_to):
    list = ['月ごとの稼働率推移','時間帯ごとの稼働率','入庫時間帯ごとの滞在時間','滞在時間割合']
    st.dataframe(df)
    st.pyplot(fig)

#入出庫データ表作成用
def putIO_in_order(df):
    date_list = df['入庫日'].unique()
    N_in,N_out = [],[]
    
    for date in date_list:
        list_in,list_out = [],[]

        for i in range(24):
            list_in.append(
                ((df['入庫時間帯']==i)&(df['入庫日']==date)).sum()
            )
            list_out.append(
                ((df['出庫時間帯']==i)&(df['出庫日']==date)).sum()
            )

        list_in.append(
            (df['入庫日']==date).sum()
        )
        list_out.append(
            (df['出庫日']==date).sum()
        )

        N_in.append(list_in)
        N_out.append(list_out)

    df_in = pd.DataFrame(data=N_in,index=date_list)
    df_out = pd.DataFrame(data=N_out,index=date_list)
    df_in.rename(columns={24:'合計'},inplace=True)
    df_out.rename(columns={24:'合計'},inplace=True)

    df_diff = pd.DataFrame(data=0,columns = df_in.columns,index = df_in.index)
    for i in range(24):
        df_diff[i] = df_in[i] - df_out[i]
    df_diff['合計'] = df_in['合計'] - df_out['合計']

    #日ごとの売上集計（出庫ベース）
    sales = []
    for date in date_list:
        list = []
        list.append(
            df.query('出庫日==@date')['課金額'].sum()
            )    
        sales.append(list)

    df_in['売上'] = sales
    df_out['売上'] = sales
    df_diff['売上'] = sales

    return df_in,df_out,df_diff

def resample_df(df_in,rule):
    df_in.index = pd.to_datetime(df_in.index)
    df_in = df_in.resample(rule=rule_dict[rule][0]).sum().reset_index()
    df_in['index'] = df_in['index'].dt.strftime(rule_dict[rule][1])
    df_in = df_in.set_index('index')
    df_in.loc['合計'] = [df_in[i].sum() for i in range(24)] + [df_in['合計'].sum()]

    return df_in

#コロナ感染者数推移
#コロナ感染者数dataframe作成用
def make_codf(codata_path):
    codf = pd.read_csv(codata_path)
    codf['Date'] = pd.to_datetime(codf['Date'])
    codf = codf.set_index('Date')
    codf = codf.resample('M').mean().reset_index()
    codf['Date'] = codf['Date'].dt.strftime('%Y-%m')
    codf = codf.set_index('Date')
    return codf

#コロナ感染者推移グラフ描画用
def plot_covid_data(codf,date_from,date_to,city):
    dataframe = codf.query('@date_from <= Date <= @date_to')
    dataframe = dataframe.loc[:,city]

    plt.rcParams['font.size'] = 6
    fig,ax = plt.subplots(figsize=(7,2))
    ax.plot(dataframe.index,dataframe[city],marker='.')
    ax.set_xlabel('月')
    ax.set_ylabel('人(月平均)')
    ax.set_title( f'コロナ感染者数推移（{dataframe.index[0]}〜{dataframe.index[-1]}）' )
    ax.grid()
    ax.legend(city)
    ax.set_xticks(ticks=dataframe.index)
    plt.xticks(rotation=45)

    return dataframe.T,fig

#画面表示　ーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーー
st.set_page_config(page_title='ReadIO',layout='wide')

select = st.sidebar.radio(label='SELECT',options=['駐車場利用分析','コロナ感染者推移'])
st.sidebar.header('')

if select == '利用方法':
    how_to_use()

elif select == '駐車場利用分析':  
    # menu = st.sidebar.radio(label='MENU',options=['基本データ','簡易利用分析','入出庫データ表'])

    file_path = st.file_uploader('excelデータをアップロード ※csvデータを使う場合はexcelに変換してから',type='xlsx')
    if file_path:

        df = make_df(file_path)
        # name = st.sidebar.text_input('事業地名',value='リパーク')
        capacity = st.sidebar.number_input(label='駐車可能台数',min_value=1,value=10)
        date_from,date_to = st.sidebar.select_slider(label='表示データを期間で制限',
                                            options=df['入庫日'].unique().tolist(),
                                            value=(df['入庫日'].unique().tolist()[0],df['入庫日'].unique().tolist()[-1]))
        fee_from,fee_to = st.sidebar.slider(label='表示データを課金額で制限',
                                    min_value=df['課金額'].min(),max_value=df['課金額'].max(),
                                    value=(df['課金額'].min(),df['課金額'].max()) )

        df = df.query('@date_from<=出庫日<=@date_to & @fee_from<=課金額<=@fee_to')
        df1,fig1 = plt_occupancy_trans(df,capacity)
        df2,fig2 = plt_occupancy_rate(df,capacity)
        df3,fig3 = plt_stay_bar(df)
        df4,fig4 = plt_stay_pie(df)

        with st.expander('DataFrame'):
            st.dataframe(df.loc[:,['入庫日時','出庫日時','滞在時間','入庫曜日','課金額']])

        with st.expander('基本データ'):
            n = len(df.index)
            d = df['入庫日'].nunique()
            st.write(f"データ期間：{df['入庫日'].unique().tolist()[0]} 〜 {df['入庫日'].unique().tolist()[-1]}（計{d}日）")
            st.write(f"利用総台数：{n}台　1日あたり利用台数：{round(n/d)}台")
            st.write(f"平均滞在時間：{round(df['滞在時間（分）'].mean())}分　平均課金額：{round(df['課金額'].mean())}円")
            
        with st.expander('月ごとの稼働率推移'):
            show_data(1,df1,fig1,date_from,date_to)
        with st.expander('時間帯ごとの稼働率'):
            show_data(2,df2,fig2,date_from,date_to)
        with st.expander('入庫時間帯ごとの滞在時間'):
            show_data(3,df3,fig3,date_from,date_to)
        with st.expander('滞在時間割合'):
            show_data(4,df4,fig4,date_from,date_to)
        
        with st.expander('入出庫データ表'):
            df_in,df_out,df_diff = putIO_in_order(df)
            rule_dict = {
                '日次合計':['D','%Y-%m-%d'],
                '週次合計':['W','%Y-%m-%d'],
                '月次合計':['M','%Y-%m'],
                '四半期合計':['Q','%Y-%m'],
                '年次合計':['Y','%Y'],
                }
            select = st.selectbox(
                label='選択',
                options=['入庫台数表','出庫台数表','差し引き入庫台数表']
                )
            rule = st.selectbox(label='集計方法',options=rule_dict.keys())

            df_in_resampled = resample_df(df_in,rule)
            df_out_resampled = resample_df(df_out,rule)
            df_diff_resampled = resample_df(df_diff,rule)

            if select == '入庫台数表':
                st.write('時間帯ごとの入庫台数　※index列には集計期間の最終日が表示されます')
                st.dataframe(df_in_resampled)

            elif select == '出庫台数表':
                st.write('時間帯ごとの出庫台数　※index列には集計期間の最終日が表示されます')
                st.dataframe(df_out_resampled)

            elif select == '差し引き入庫台数表':
                st.write('時間帯ごとの差し引き入庫台数（入庫台数ー出庫台数）　※index列には集計期間の最終日が表示されます')
                st.dataframe(df_diff_resampled)
                io_model = pd.DataFrame(data=[df_diff[i].mean() for i in range(24)],columns=['差し引き入庫台数（1日あたり）']).T
                st.write(io_model)

            else:
                pass

elif select == 'コロナ感染者推移':
    st.write('厚生労働省のデータリンク先→https://www.mhlw.go.jp/stf/covid-19/open-data.html')
    codata_path = st.file_uploader('コロナデータをアップロード',type=['csv'])

    if codata_path:
        codf = make_codf(codata_path)
        date_from,date_to = st.sidebar.select_slider(label='期間',options=codf.index,value=(codf.index[0],codf.index[-1]))
        city = st.sidebar.multiselect(label = '表示する列名を選択(初期設定は広島県):',options = codf.columns,default = 'Hiroshima')

        df_co,fig_co = plot_covid_data(codf,date_from,date_to,city)
        st.dataframe(df_co)
        st.pyplot(fig_co)