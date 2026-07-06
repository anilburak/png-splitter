import pandas as pd


def calculate(frame, work_days, daily_hours):
    data = frame.copy()
    data["required_hours"] = data["quantity"] * data["cycle_seconds"] / 3600
    capacity = work_days * daily_hours
    grouped = data.groupby("machine", dropna=False)["required_hours"].sum().reset_index()
    grouped["capacity_hours"] = capacity
    grouped["usage_percent"] = grouped["required_hours"] / capacity * 100 if capacity else 0
    grouped["status"] = pd.cut(grouped["usage_percent"], [-1, 85, 100, float("inf")], labels=["Uygun", "Riskli", "Kapasite Aşımı"], right=False).astype(str)
    return data, grouped.sort_values("usage_percent", ascending=False).reset_index(drop=True)
