"""グラフにする."""
import argparse
import datetime
import operator
import os
import pandas as pd
import typing as typ
import bokeh.models as bm
import bokeh.plotting as bp


def read_log(logfile: os.DirEntry) -> pd.DataFrame:
    """ログを読む.

    Args:
        logpath: ログファイルのDirEntry

    Returns:
        DataFrame
    """
    df = pd.read_csv(logfile.path, skipinitialspace=True)
    timestr: str = logfile.name[:-4]
    filetime: datetime.datetime = datetime.datetime.strptime(timestr, "%Y%m%d_%H%M%S")
    df["timestamp"] = filetime
    return df


def read_logs(logdir: str) -> pd.DataFrame:
    """ログを読む.

    Args:
        logdir: ログディレクトリ

    Returns:
        DataFrame
    """
    dfs: typ.List[pd.DataFrame] = []
    for logfile in sorted(os.scandir(logdir), key=operator.attrgetter("name")):
        if logfile.name.endswith(".csv"):
            dfs.append(read_log(logfile))
    return pd.concat(dfs)


def make_graph(df: pd.DataFrame, interface: typ.Optional[str], outdir: str, period: int) -> None:
    """グラフを描く.

    Args:
        df: DataFrame
        interface: グラフにする系列
        outdir: 出力ディレクトリ
        period: データ量の間隔(秒)
    """
    if interface is None:
        df_t: pd.DataFrame = df[df["ポート名"] != "TA"].groupby("timestamp").sum().reset_index()
    else:
        df_t = df[df["ポート名"] == interface].copy()
    df_t["受信したデータ量(Mbyte)"] = df_t["受信したデータ量(byte)"] / (1024 * 1024)
    df_t["送信したデータ量(Mbyte)"] = df_t["送信したデータ量(byte)"] / (1024 * 1024)
    df_t["受信したデータ量(Gbyte)"] = df_t["受信したデータ量(byte)"] / (1024 * 1024 * 1024)
    df_t["送信したデータ量(Gbyte)"] = df_t["送信したデータ量(byte)"] / (1024 * 1024 * 1024)
    source: bp.ColumnDataSource = bp.ColumnDataSource(df_t)
    tooltips: typ.List[typ.Tuple[str, str]] = [
        ("time", "@timestamp{%F %T}"),
        ("下り", "@{送信したデータ量(Gbyte)}{0,0.0}[GB]"),
        ("上り", "@{受信したデータ量(Gbyte)}{0,0.0}[GB]"),
    ]
    hover_tool: bm.HoverTool = bm.HoverTool(tooltips=tooltips, formatters={"@timestamp": "datetime"})
    bp.output_file(os.path.join(outdir, f"{interface}_acc.html"), title=interface)
    fig: bp.figure = bp.figure(
        title=f"{interface} の累積データ量",
        x_axis_type="datetime",
        x_axis_label="時刻",
        y_axis_label="データ量[GB]",
        sizing_mode="stretch_both",
    )
    fig.add_tools(hover_tool)
    fmt: typ.List[str] = ["%H:%M"]
    fig.xaxis.formatter = bm.DatetimeTickFormatter(hours=fmt, hourmin=fmt, minutes=fmt)
    fig.y_range = bm.Range1d(0, df_t[["受信したデータ量(Gbyte)", "送信したデータ量(Gbyte)"]].max().max() * 1.1)
    fig.line("timestamp", "送信したデータ量(Gbyte)", legend_label="下り", line_color="green", source=source)
    fig.line("timestamp", "受信したデータ量(Gbyte)", legend_label="上り", line_color="red", source=source)
    fig.legend.click_policy = "hide"
    fig.legend.location = "top_left"
    bp.save(fig)

    df_d: pd.DataFrame = df_t[["timestamp", "受信したデータ量(Mbyte)", "送信したデータ量(Mbyte)"]].diff()
    df_d = df_d[["受信したデータ量(Mbyte)", "送信したデータ量(Mbyte)"]].div(df_d["timestamp"].dt.total_seconds(), axis=0) * period
    df_d = pd.concat([df_t[["timestamp"]], df_d], axis=1).iloc[1:]
    source = bp.ColumnDataSource(df_d)
    tooltips = [
        ("time", "@timestamp{%F %T}"),
        ("下り", "@{送信したデータ量(Mbyte)}{0,0.0}[MB]"),
        ("上り", "@{受信したデータ量(Mbyte)}{0,0.0}[MB]"),
    ]
    hover_tool = bm.HoverTool(tooltips=tooltips, formatters={"@timestamp": "datetime"})
    bp.output_file(os.path.join(outdir, f"{interface}_diff.html"), title=interface)
    periodstr: str = f"{period}秒"
    periodunits: typ.Dict[int, str] = {86400: "日", 3600: "時間", 60: "分"}
    for unit, unitstr in periodunits.items():
        if period >= unit:
            if period % unit == 0:
                periodstr = f"{period // unit}{unitstr}"
            else:
                periodstr = f"{period / unit}{unitstr}"
            break
    fig = bp.figure(
        title=f"{interface} の{periodstr}あたりのデータ量",
        x_axis_type="datetime",
        x_axis_label="時刻",
        y_axis_label="データ量[MB]",
        sizing_mode="stretch_both",
    )
    fig.add_tools(hover_tool)
    fig.xaxis.formatter = bm.DatetimeTickFormatter(hours=fmt, hourmin=fmt, minutes=fmt)
    fig.y_range = bm.Range1d(0, df_d[["受信したデータ量(Mbyte)", "送信したデータ量(Mbyte)"]].max().max() * 1.1)
    fig.line("timestamp", "送信したデータ量(Mbyte)", legend_label="下り", line_color="green", source=source)
    fig.line("timestamp", "受信したデータ量(Mbyte)", legend_label="上り", line_color="red", source=source)
    fig.legend.click_policy = "hide"
    fig.legend.location = "top_left"
    bp.save(fig)


def main() -> None:
    """メイン."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("-l", "--logdir", help="path of log directory", default="log")
    parser.add_argument("-o", "--outdir", help="path of output directory", default="graph")
    parser.add_argument("-p", "--period", type=int, help="period of graph[seconds]", default=3600)
    parser.add_argument("-i", "--interface", help="interface")
    args: argparse.Namespace = parser.parse_args()
    df: pd.DataFrame = read_logs(args.logdir)
    make_graph(df, args.interface, args.outdir, args.period)


if __name__ == "__main__":
    main()
