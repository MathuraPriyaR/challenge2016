import streamlit as st
import json
import csv

# ========== Permission Checker Class ==========
class PermissionChecker:
    def __init__(self, cities_file, distributors_file):
        self.city_map = {}
        self.distributors_file = distributors_file
        self.distributors = {}
        self.load_cities(cities_file)
        self.load_distributors(distributors_file)

    def load_cities(self, cities_file):
        with open(cities_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                city_code = row["City Code"].strip()
                province_code = row["Province Code"].strip()
                country_code = row["Country Code"].strip()

                city_key = f"{city_code}-{province_code}-{country_code}"
                state_key = f"{province_code}-{country_code}"
                country_key = country_code

                self.city_map[city_key] = {"state": state_key, "country": country_key}
                self.city_map[state_key] = {"country": country_key}
                self.city_map[country_key] = {}

    def load_distributors(self, distributors_file):
        with open(distributors_file, encoding="utf-8") as f:
            data = json.load(f)
            for dist in data["distributors"]:
                self.distributors[dist["name"]] = dist

    def save_distributors(self):
        with open(self.distributors_file, "w", encoding="utf-8") as f:
            json.dump({"distributors": list(self.distributors.values())}, f, indent=4)

    def resolve_permissions(self, distributor_name):
        if distributor_name not in self.distributors:
            return set(), set()

        dist = self.distributors[distributor_name]
        include = set(dist.get("INCLUDE", []))
        exclude = set(dist.get("EXCLUDE", []))

        if "Authorized_by" in dist:
            parent_incl, parent_excl = self.resolve_permissions(dist["Authorized_by"])
            include |= parent_incl
            exclude |= parent_excl

        return include, exclude

    def check_permission(self, distributor_name, place):
        include, exclude = self.resolve_permissions(distributor_name)

        if place in exclude:
            return "No"

        hierarchy = [place]
        if place in self.city_map:
            if "state" in self.city_map[place]:
                hierarchy.append(self.city_map[place]["state"])
            if "country" in self.city_map[place]:
                hierarchy.append(self.city_map[place]["country"])

        for h in hierarchy:
            if h in exclude:
                return "No"
        for h in hierarchy:
            if h in include:
                return "Yes"
        return "No"


# ========== Streamlit App ==========
checker = PermissionChecker("cities.csv", "distributors.json")

st.title("📍 Distributor Permission Checker")

# --- Permission Checker Section ---
st.header("🔍 Check Permission")
dist_name = st.selectbox("Choose Distributor", list(checker.distributors.keys()))
place = st.text_input("Enter Place Code (e.g., KLRAI-TN-IN, TN-IN, IN)")
if st.button("Check"):
    if place:
        result = checker.check_permission(dist_name, place)
        if result == "Yes":
            st.success(f"Permission for {dist_name} in {place}: **{result}**")
        else:
            st.error(f"Permission for {dist_name} in {place}: **{result}**")

# --- View Distributors Section ---
st.header("📋 Current Distributors")
for d, info in checker.distributors.items():
    st.subheader(d)
    st.json(info)

# --- Update Distributors Section ---
st.header("✏️ Update Distributor")
with st.form("update_form"):
    new_name = st.text_input("Distributor Name")
    include_list = st.text_area("INCLUDE (comma-separated codes)").split(",")
    exclude_list = st.text_area("EXCLUDE (comma-separated codes)").split(",")
    authorized_by = st.text_input("Authorized_by (optional)").strip()
    submitted = st.form_submit_button("Save Distributor")

    if submitted and new_name:
        checker.distributors[new_name] = {
            "name": new_name,
            "INCLUDE": [x.strip() for x in include_list if x.strip()],
            "EXCLUDE": [x.strip() for x in exclude_list if x.strip()],
        }
        if authorized_by:
            checker.distributors[new_name]["Authorized_by"] = authorized_by
        checker.save_distributors()
        st.success(f"Distributor '{new_name}' updated/added successfully!")
