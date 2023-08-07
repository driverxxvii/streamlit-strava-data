import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime, timedelta


@st.cache_data
def read_csv(csv_file):
    df = pd.read_csv(csv_file)

    # Create helper columns
    # Convert duration in seconds to hr:min:secs
    df["Ride Time"] = pd.to_datetime(df["Duration"], unit="s").dt.strftime("%H:%M:%S")
    df["Activity Date"] = pd.to_datetime(df["Activity Date"], format="%Y-%m-%d")
    df["MonthNum"] = df["Activity Date"].dt.strftime("%m")  # month number 01, 02, 03... (string)
    df["Month"] = df["Activity Date"].dt.strftime("%b")  # month name Jan, Feb

    df["Year"] = df["Activity Date"].dt.strftime("%Y")
    df = df.astype({"Year": "int"})  # change "Year" to integer

    df["Avg Speed"] = round((df["Distance"] / df["Duration"]) * 3600, 2)

    # Columns in df
    # Recorded On,Activity Date,Start Time,Finish Time,Distance,Duration,Max Speed
    # Ride Time, MonthNum, Year, Avg Speed

    return df


def monthly_summary_by_year(df, year):
    """
    Aggregates by month number.
    """
    condition = df["Year"] == year
    df = df[condition]
    month_group = df.groupby(["MonthNum"])
    aggregator = "Distance"
    summary_stats = ["sum", "count", "mean", "max"]
    monthly_summary_df = month_group[aggregator].agg(summary_stats).round(3)

    # Create a month name column
    monthly_summary_df["Month"] = pd.to_datetime(monthly_summary_df.index, format="%m").strftime("%b")

    monthly_summary_df.rename(columns={"sum": "Distance",
                                       "count": "Rides",
                                       "mean": "Avg Dist"}, inplace=True)

    # print(monthly_summary_df)
    return monthly_summary_df


def top_n_days(df, n):
    # df["Activity Date"] = pd.to_datetime(df["Activity Date"])  # change to datetime data type
    date_group = df.groupby(["Activity Date"])
    aggregator = "Distance"
    summary_stats = ["sum", "count", "mean"]
    day_agg = date_group[aggregator].agg(summary_stats).round(3)
    top_n_days_df = day_agg.nlargest(n, "sum")
    # print(top_n_days_df)
    return top_n_days_df


def top_n_rides(df, n):
    top_n_rides_df = df.nlargest(n, "Distance")
    top_n_rides_df.drop(["Recorded On", ], axis=1, inplace=True)
    return top_n_rides_df


def top_max_speeds(df, n):
    max_speeds_df = df.nlargest(n, "Max Speed")
    max_speeds_df.drop(["Recorded On", "Finish Time"], axis=1, inplace=True)
    return max_speeds_df


def summary_metrics(df):
    total_dist = f"{df['Distance'].sum():.5g}"
    # total_dist = f"{total_dist:.5g}"
    total_duration = df["Duration"].sum()
    hrs = int(total_duration / 3600)
    mins = int((total_duration % 3600) / 60)
    sec = int(total_duration % 60)
    total_duration = f"{hrs:02}:{mins:02}:{sec:02}"

    rides = len(df)
    active_days = df['Activity Date'].nunique()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(label="Total Distance", value=f"{total_dist} km")
    c2.metric(label="Total Time", value=total_duration)
    c3.metric(label="Number of rides", value=rides)
    c4.metric(label="Active days", value=active_days)


def st_lit(df):
    st_lit_last4weeks(df)
    st_lit_monthly_summary(df)
    st_lit_monthly_totals(df)
    st_lit_longest_rides(df)


def st_lit_monthly_summary(df):
    st.subheader(f"Monthly summary by year")
    years = df["Year"].unique().tolist()
    year = st.selectbox("Year", years, index=len(years) - 1)

    year_df = df.loc[df["Year"] == year]
    summary_metrics(year_df)

    monthly_summary_df = monthly_summary_by_year(df, year)
    monthly_summary_df.set_index("Month", inplace=True)
    fig = px.bar(monthly_summary_df, y="Distance",
                 title=f"Monthly summary for {year}",
                 # text="Distance",
                 text_auto=".4g",
                 )
    fig.update_traces(marker_color="#287274")
    st.plotly_chart(fig)
    st.dataframe(monthly_summary_df, height=460)


def st_lit_longest_rides(df):
    # Top rides section
    st.subheader(f"Longest rides so far by distance (km)")
    col1, col2 = st.columns(2)

    top_n = col1.text_input("Number of rides to show", value=5)
    years = df["Year"].unique().tolist()
    years.append("All")
    # last item in list is "All", select one before last item by default
    year_filter = col2.selectbox("Filter by year", years, index=len(years) - 2)

    # Get a filtered df by year
    if year_filter != "All":
        condition = df["Activity Date"].dt.strftime("%Y") == str(year_filter)
        filtered_df = df[condition]
    else:
        filtered_df = df

    # pass filtered df to top_n_rides function to get top rides from that year
    top_n_df = top_n_rides(filtered_df, int(top_n))
    top_n_df = top_n_df[["Activity Date", "Distance", "Ride Time", "Avg Speed"]]

    # Format "Activity Date" as string so that it displays correctly in streamlit
    top_n_df.reset_index(drop=True)
    top_n_df["Activity Date"] = top_n_df["Activity Date"].dt.strftime("%b %d, %Y")

    st.dataframe(top_n_df)


def st_lit_monthly_totals(df):
    st.subheader(f"Monthly totals in Km")
    pivot_df = df.pivot_table(values="Distance",
                              index=["MonthNum", "Month"],  # multi index month to sort correctly by month
                              columns="Year",
                              aggfunc="sum",
                              fill_value=0,
                              margins=True,
                              margins_name="Total")

    pivot_df = pivot_df.droplevel(0)  # Remove monthnum by dropping a level from multi-index

    # The row "Total" from margins_name is added to the top level index that is dropped
    # Add it to the last row of the "Month" column
    pivot_df = pivot_df.rename(index={pivot_df.index[-1]: "Yearly Totals"})
    st.dataframe(pivot_df, width=700, height=500)


def st_lit_last4weeks(df):
    st.subheader(f"The Last 4 Weeks")
    condition = df["Activity Date"] >= datetime.now() - timedelta(weeks=4)
    last4weeks_df = df[condition]

    summary_metrics(last4weeks_df)

    last4weeks_df = last4weeks_df[["Activity Date", "Distance", "Ride Time",
                                   "Avg Speed",
                                   "Duration",
                                   ]]

    # Group by day to show in second tab of bar graph
    last4weeks_df_group_day = last4weeks_df.groupby("Activity Date")[
        ["Distance", "Duration"]].agg(["sum"])
    last4weeks_df_group_day = last4weeks_df_group_day.droplevel(1, axis=1)
    last4weeks_df_group_day["Ride Time"] = pd.to_datetime(last4weeks_df_group_day["Duration"], unit="s").dt.strftime("%H:%M:%S")
    last4weeks_df_group_day["Avg Speed"] = \
        round((last4weeks_df_group_day["Distance"] / last4weeks_df_group_day["Duration"]) * 3600, 2)
    print(last4weeks_df_group_day)
    tab1, tab2 = st.tabs(["By Ride", "By Day"])
    with tab1:
        fig = px.bar(last4weeks_df,
                     x="Activity Date",
                     y="Distance",
                     title="Daily activity in the last 4 weeks",
                     hover_data=["Ride Time"],
                     # color=round(last4weeks_df["Duration"] / 60, 2),
                     color="Avg Speed",
                     color_continuous_scale="mint",
                     # color_continuous_scale="rbg",
                     text_auto=True)

        fig.update_layout(width=800,)
        st.plotly_chart(fig)

    with tab2:
        fig = px.bar(last4weeks_df_group_day,
                     y="Distance",
                     title="Daily activity in the last 4 weeks",
                     hover_data=["Ride Time"],
                     color="Avg Speed",
                     color_continuous_scale="mint",
                     text_auto=True)

        fig.update_layout(width=800)
        st.plotly_chart(fig)

    with st.expander("See the data"):
        tab3, tab4 = st.tabs(["By Ride", "By Day"])
        with tab3:
            last4weeks_df["Date"] = last4weeks_df["Activity Date"].dt.strftime("%b %d, %Y")
            last4week_df_table = last4weeks_df[["Date", "Distance", "Ride Time", "Avg Speed"]]
            last4week_df_table.set_index("Date", inplace=True)
            st.dataframe(last4week_df_table, width=400)
        with tab4:
            last4weeks_df_group_day["Date"] = last4weeks_df_group_day.index.strftime("%b %d, %Y")
            last4weeks_df_group_day_df_table = last4weeks_df_group_day[["Date", "Distance", "Ride Time", "Avg Speed"]]
            last4weeks_df_group_day_df_table.set_index("Date", inplace=True)
            st.dataframe(last4weeks_df_group_day_df_table, width=400)
        # st.dataframe(last4week_df_table.style.highlight_max(axis=0), width=400)


def main():
    csv_file_path = r"C:\Users\User1\My Drive\09 Python Projects\Strava_Cycling_Data\cycling_data.csv"
    df = read_csv(csv_file_path)
    # print(monthly_summary_by_year(df, 2023))
    # print(top_n_days(df, 10))
    # print(top_n_rides(df, 10))
    # top_max_speeds(df, 30)
    st_lit(df)


if __name__ == "__main__":
    main()
