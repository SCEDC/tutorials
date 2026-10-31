#!/usr/bin/env python3
"""Download waveforms for every phase arrival of the 2004 M6 Parkfield earthquake.

It is an example of retrieving data from multiple data sources.
Phases come from the ComCat 'nc' phase-data product for nc30228270. For each
arrival, the picked channel is requested with FDSN get_waveforms from the
arrival time to arrival + 60 s. The data center that normally archives the
network is tried first (CI -> SCEDC, everything else -> NCEDC), then the other.
If the picked location code returns nothing, any location code is tried.
"""
# ---------------------------------------------------------------------------
# Tutorial overview
# ---------------------------------------------------------------------------
# This script shows a common seismology workflow built from two kinds of
# web services:
#
#   1. An *event* service (USGS ComCat) to find out what happened: where and
#      when the earthquake was, and which stations recorded which phases
#      (the "picks").
#   2. *Waveform* services (FDSN dataselect at SCEDC and NCEDC) to download
#      the actual ground-motion time series around each pick.
#
# FDSN (International Federation of Digital Seismograph Networks) defines
# standard web-service APIs that most data centers implement:
#
#   fdsnws/event/1/       earthquake catalogs   -> QuakeML (XML), GeoJSON, text
#   fdsnws/station/1/     station metadata      -> StationXML, text
#   fdsnws/dataselect/1/  waveform data         -> miniSEED
#
# Because the APIs are the same everywhere, ObsPy's FDSN Client can talk to
# any of these data centers with identical code -- only the name changes.
#
# Key ObsPy objects used below:
#
#   Catalog -> Event -> Origin  -> Arrival   (one per phase used in location)
#                    -> Pick                  (the measured onset time)
#   Stream  -> Trace -> .data (numpy array), .stats (metadata)
#   UTCDateTime        a timestamp you can add/subtract seconds from
#
# Run with --help to see the command-line options.
# ---------------------------------------------------------------------------
import argparse
import csv
import json
import os
import urllib.request

# read_events parses QuakeML (and many other catalog formats) into an
# obspy Catalog object.
from obspy import read_events
# Client is ObsPy's generic FDSN web-service client. Client("SCEDC") looks up
# the SCEDC base URL (https://service.scedc.caltech.edu) from ObsPy's built-in
# list; you can also pass a full URL for data centers not in that list.
from obspy.clients.fdsn import Client
# The FDSN services answer "nothing matched" with HTTP 204 (No Content);
# ObsPy turns that into this exception rather than returning an empty Stream.
from obspy.clients.fdsn.header import FDSNNoDataException

# ComCat event IDs are the contributing network code + that network's own ID.
# "nc" = Northern California Seismic System, which located this event.
EVENTID = "nc30228270"
# The ComCat FDSN event service. With an eventid and format=geojson it returns
# a "detail" document listing every product (origins, moment tensors,
# ShakeMaps, phase data, ...) contributed for the event, with download URLs.
# Try pasting this URL into a browser to see what it contains.
DETAIL_URL = ("https://earthquake.usgs.gov/fdsnws/event/1/query"
              f"?eventid={EVENTID}&format=geojson")
# Networks whose data are archived at SCEDC (Southern California); Parkfield
# is in central California, so most stations belong to NCEDC networks
# (NC, BK, BP, ...).
SCEDC_NETS = {"CI", "AZ", "ZY"}
# Approximate km per degree of great-circle arc. QuakeML stores epicentral
# distance in degrees.
DEG2KM = 111.19


def fetch_phases(outdir):
    """Download the nc phase-data QuakeML and return the parsed event."""
    # Step 1: ask ComCat for the event detail (GeoJSON = plain JSON).
    with urllib.request.urlopen(DETAIL_URL) as f:
        detail = json.load(f)
    # The "phase-data" product contains the origin plus all picks and
    # arrivals. Several networks may contribute one, so pick the "nc" copy,
    # which belongs to the authoritative location.
    products = detail["properties"]["products"]["phase-data"]
    nc = next(p for p in products if p["source"] == "nc")
    # Step 2: each product lists its files under "contents". Save the QuakeML
    # file locally so it can be inspected later and the run is reproducible.
    path = os.path.join(outdir, f"{EVENTID}_phases.xml")
    urllib.request.urlretrieve(nc["contents"]["quakeml.xml"]["url"], path)
    # Step 3: read_events returns a Catalog (a list of Events); this file
    # holds only one event, so take element [0].
    #
    # Tip: for plain catalog searches (by time, region, magnitude) you would
    # normally use Client("USGS").get_events(...) instead of building URLs
    # by hand. Here we go through the GeoJSON detail because the phase-data
    # product is only reachable that way.
    return read_events(path)[0]


def get_waveform(clients, order, wid, t0, t1):
    """Try each data center and location code; return (stream, center, loc)."""
    # A channel is identified by its SEED code NET.STA.LOC.CHA, for example
    # NC.PMM..HHZ: network NC, station PMM, empty location, channel HHZ
    # (H = high sample rate, H = high-gain seismometer, Z = vertical).
    #
    # FDSN services spell an empty location code as "--". The location code
    # in a pick does not always match what the archive uses, so if the exact
    # one fails we retry with the wildcard "*" (any location). get_waveforms
    # also accepts "?" wildcards and comma-separated lists in each field.
    locs = [wid.location_code or "--"]
    if locs[0] != "*":
        locs.append("*")
    for name in order:
        for loc in locs:
            try:
                # The core FDSN dataselect request. Arguments are
                # network, station, location, channel, starttime, endtime;
                # t0 and t1 are UTCDateTime objects. The result is an ObsPy
                # Stream: a list of Trace objects, one per contiguous chunk
                # of data. For many channels at once, see
                # Client.get_waveforms_bulk(), which is much faster than a
                # loop of single requests.
                #
                # Add attach_response=True here if you plan to remove the
                # instrument response later with st.remove_response().
                st = clients[name].get_waveforms(
                    wid.network_code, wid.station_code, loc,
                    wid.channel_code, t0, t1)
            except FDSNNoDataException:
                # No data at this center for this request; try the next one.
                continue
            if len(st):
                return st, name, loc
    return None, None, None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outdir", default="waveforms")
    ap.add_argument("--before", type=float, default=0.0,
                    help="seconds before the arrival to start (default 0)")
    ap.add_argument("--after", type=float, default=60.0,
                    help="seconds after the arrival to end (default 60)")
    ap.add_argument("--ref", choices=["arrival", "origin"], default="arrival",
                    help="time that --before/--after are measured from")
    ap.add_argument("--max-km", type=float,
                    help="only arrivals within this epicentral distance")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    event = fetch_phases(args.outdir)
    # An Event can carry several Origins (solutions from different methods or
    # agencies); preferred_origin() is the one the catalog considers best.
    # Some files don't mark a preferred origin, so fall back to the first.
    origin = event.preferred_origin() or event.origins[0]
    # In QuakeML, objects reference each other by resource_id (like a foreign
    # key). Each Arrival has a pick_id pointing at a Pick, so build a lookup
    # table from resource_id to Pick.
    picks = {p.resource_id: p for p in event.picks}
    # Create each client once and reuse it. Creating a Client contacts the
    # server to discover which services it offers, so don't create one per
    # request.
    clients = {"SCEDC": Client("SCEDC"), "NCEDC": Client("NCEDC")}

    rows = []
    # origin.arrivals are the phases used to locate this origin. Each one adds
    # location-specific info to its pick: phase name, distance, residual,
    # weight, ...
    for arr in origin.arrivals:
        # arr.distance is the epicentral distance in degrees.
        if args.max_km and arr.distance * DEG2KM > args.max_km:
            continue
        pick = picks[arr.pick_id]
        # waveform_id is a WaveformStreamID: the NET/STA/LOC/CHA of the
        # channel the pick was made on.
        wid = pick.waveform_id
        # The phase label (P, S, Pn, ...) may be on the arrival, the pick,
        # or missing entirely; "X" marks unknown.
        phase = arr.phase or pick.phase_hint or "X"
        order = (["SCEDC", "NCEDC"] if wid.network_code in SCEDC_NETS
                 else ["NCEDC", "SCEDC"])
        # pick.time and origin.time are UTCDateTime objects. Adding or
        # subtracting a number shifts them by that many seconds.
        ref = pick.time if args.ref == "arrival" else origin.time
        t0, t1 = ref - args.before, ref + args.after
        st, center, loc = get_waveform(clients, order, wid, t0, t1)

        row = {"id": wid.get_seed_string(), "phase": phase,
               "arrival": str(pick.time), "distance_deg": arr.distance,
               "center": center or "", "loc_used": loc or "", "file": "",
               "traces": 0}
        if st is None:
            print(f"no data  {row['id']} {phase}")
        else:
            # A gap in the data (telemetry dropout, etc.) makes the server
            # return several Traces for one channel. merge() joins them into
            # one Trace per channel; method=1 resolves overlapping samples,
            # and any remaining gaps become masked (numpy.ma) values.
            st.merge(method=1)
            # Every Trace has a .stats header with network, station,
            # location, channel, starttime, sampling_rate, npts, ... Use the
            # location code the server actually returned, which may differ
            # from the pick's if the "*" fallback was used.
            fname = (f"{wid.network_code}.{wid.station_code}."
                     f"{st[0].stats.location}.{wid.channel_code}.{phase}"
                     f".{pick.time.strftime('%H%M%S')}.mseed")
            path = os.path.join(args.outdir, fname)
            # miniSEED cannot store masked arrays, so if merge() left gaps,
            # split() turns the Stream back into gap-free Traces.
            if any(hasattr(tr.data, "mask") for tr in st):
                st = st.split()
            # Stream.write supports many formats (MSEED, SAC, ...). miniSEED
            # is the standard archive format and keeps all the SEED IDs. Read
            # files back with obspy.read("waveforms/*.mseed").
            st.write(path, format="MSEED")
            row.update(file=fname, traces=len(st))
            print(f"{center:5s}    {row['id']} {phase} -> {fname}")
        rows.append(row)

    # Write a summary of what was found, including which data center served
    # each channel, so missing data can be followed up later.
    with open(os.path.join(args.outdir, "summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    got = sum(1 for r in rows if r["file"])
    print(f"\n{got}/{len(rows)} arrivals with data; see "
          f"{os.path.join(args.outdir, 'summary.csv')}")


if __name__ == "__main__":
    main()
