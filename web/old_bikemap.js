// see if they're on a sleek sexy phone
var isIphone = /iphone/i.test(navigator.userAgent);
var isAndroid = /android/i.test(navigator.userAgent);

var BASEURL = self.location.href.replace(self.location.search, "").replace(/\/$/, "");	// why is this the only thing I capitalized
var geocoder = new GClientGeocoder(); // why is this init'd in the middle of nowhere

/*
onLoad:
0. init mobile, add event handlers, etc.
1. populate form fields w/ preset values (greyed out)
2. request user's location via geolocation API if present
3. if location was present, reverse geocode to get approxmiate address
   (TODO - offer 'my current location' option that uses lat/lng directly
   and shows user where they are on the map-- reverse geocoding loses precision)
4. repopulate 'start' w/ current address if it was found
*/

$(function() {	//document ready
	if (isIphone) {	// scroll the urlbar out of sight
		setTimeout(function() {window.scrollTo(0, 1);}, 0);
	}
	$("body").toggleClass("mobile", isIphone || isAndroid);
	$("#inputForm :input").attr("disabled", false);

	$("#inputForm").submit(function() {
		$(":input", this).attr("disabled", true);
		geocodeStartAndEndPts();
		return false;
	});

	// if they passed in start/end address, go ahead and submit the form
	var startParam = getQueryValue("start");
	var endParam = getQueryValue("end");
	var routePrefParam = getQueryValue("routePref");
	var maxSlopeParam = getQueryValue("maxSlope");
	if (startParam && endParam) {
		$("#start").val(startParam);
		$("#end").val(endParam);
		if (routePrefParam)
			$("#routePref").val(routePrefParam);
		if (maxSlopeParam)
			$("#maxSlope").val(maxSlopeParam);
		$("#inputForm").submit();
	} else {
		formDefaultValues(":input.default-value");
		if (navigator.geolocation) {
			updateStatus("Requesting current location...");
			navigator.geolocation.getCurrentPosition(onCurrentPosition, onPositionError);
		}
	}
});

// Prepopulate form fields w/ greyed out entries that disappear on focus
function formDefaultValues(selector) {
	$(selector).removeClass("active")
		.each(function() {
			if (! $(this).data("default"))
				$(this).data("default", $(this).val());
		}).focus(function() {
			if ($(this).val() == $(this).data("default"))
				$(this).val("").addClass("active");
		}).blur(function() {
			if ($(this).val() == "")
				$(this).val($(this).data("default")).removeClass("active");
		});
}

// Reverse geocode
function onCurrentPosition(position) {
	//use foundPosition flag to avoid calling this function twice due to bug in Firefox geolocation
	if (! ("foundPosition" in onCurrentPosition)) {
		var lat = position.coords.latitude;
		var lng = position.coords.longitude;
		updateStatus("Lat: " + lat + "°, Lon: " + lng + "°<br>Finding your current address...");
		geocoder.getLocations(new GLatLng(lat, lng), onReverseGeo);
		onCurrentPosition.foundPosition = true;
	}
}

// Error handler
function onPositionError(error) {
	var msg = error.message;
	if (error.code == 1 && isIphone) {
		msg += "<br><i>To re-enable on iPhone, go to: Settings->General->Reset->Reset Location Warnings (hmm actually that doesn't seem to work... iPhone bug I think)</i>";
	}
	updateStatus(msg);
}

// Update start location
// http://code.google.com/apis/maps/documentation/services.html#ReverseGeocoding
function onReverseGeo(response) {
	if (response && response.Status.code == 200) {
		var currentAddress = response.Placemark[0].address;
		if (/Francisco/.test(currentAddress)) {
			currentAddress = currentAddress.replace(/,.*$/, "");
			$("#start").val(currentAddress);
			formDefaultValues("#start");
			updateStatus("Approximate address: " + currentAddress);
		} else {
			updateStatus("Approximate address: " + currentAddress + "<br>Not in San Francisco, ignoring");
		}
	} else {
		var msg = "Reverse geocode failed. ";
		if (response)
			msg += "Response status=" + response.Status.code;
		else
			msg += "Response=null";
		updateStatus(msg);
	}
}

/*
onSubmit:
1. geocode start & end points
2. take the resulting GLatLng and find closest points in our bike graph
3. find a route from closest start to closest end pt
4. render overlay on the map and show directions

A lot of this could/should happen simultaneously in a single request on backend, but
my webhosting sucks.	So the client has to be the server, and I had to break up the
process into steps that don't take too much time.
*/

function geocodeStartAndEndPts() {
	$("#status").empty();
	$("#directions").hide();
	updateStatus("Geocoding addresses...");
	var results = {};
	$.each(["start", "end"], function(i, name) {
		geocoder.getLatLng($("#" + name).val() + ", San Francisco, CA",
			function(point) {
				if (point) {
					results[name] = gLatLngToStr(point);
					if ("start" in results && "end" in results)
						findClosestPoints(results);
				} else {
					updateStatus("Error - " + name + " address not found");
					$("#inputForm :input").attr("disabled", false);
				}
			});
	});
}

function findClosestPoints(geoResults) {
	updateStatus("Finding closest points in network");
	$.ajax({
		type: "GET",
		dataType: "json",
		url: BASEURL + "/get_pt.py",
		data: geoResults,
		success: function(points) {
			if (! points.error)
				findRoute(points);
			else
				updateStatus("Error in get_pt: " + points.msg);
		},
		error: function(request, status, exception) {
			updateStatus("Problem retrieving closest points: " + status);
			$("#inputForm :input").attr("disabled", false);
		}
	});
}

function findRoute(points) {
	updateStatus("Calculating route (may be slow...)");
	$.ajax({
		type: "GET",
		dataType: "json",
		url: BASEURL + "/find_path.py",
		data: {"start": points.startPt, "end": points.endPt, "maxSlope": $("#maxSlope").val(), "routePref": $("#routePref").val()},
		success: function(route) {
			if (! route.error)
				renderRoute(route, points.startPt, points.endPt);
			else
				updateStatus("Error in find_route: " + route.msg);
		},
		error: function(request, status, exception) {
			updateStatus("Problem finding route: " + status);
			$("#inputForm :input").attr("disabled", false);
		}
	});
}

function renderRoute(route, startPt, endPt) {
	updateStatus("Rendering route...");
	$("#gmap").show();
	var gmap = new GMap2($("#gmap")[0]);
	var gPoints = []; // array of GLatLng
	var bounds = new GLatLngBounds();
	for (var i in route.points) {
		var point = strToGLatLng(route.points[i]);
		gPoints.push(point);
		bounds.extend(point);
	}
	gmap.setCenter(bounds.getCenter(), gmap.getBoundsZoomLevel(bounds));
	gmap.addOverlay(new GPolyline(gPoints, "#0000FF", 4, 0.75));
	var uiOptions = gmap.getDefaultUI();
	uiOptions.zoom.scrollwheel = false;
	if (isIphone || isAndroid) {
		uiOptions.keyboard = false;
		uiOptions.zoom.doubleclick = false;
	}
	gmap.setUI(uiOptions);
	// add start and end points
	var greenIcon = new GIcon(G_DEFAULT_ICON);
	greenIcon.image = "http://www.google.com/mapfiles/dd-start.png";
	var startMarker = new GMarker(strToGLatLng(startPt), {clickable: false, title: "Start: " + $("#start").val(), icon: greenIcon});
	gmap.addOverlay(startMarker);
	var redIcon = new GIcon(G_DEFAULT_ICON);
	redIcon.image = "http://www.google.com/mapfiles/dd-end.png";
	var endMarker = new GMarker(strToGLatLng(endPt), {clickable: false, title: "End: " + $("#end").val(), icon: redIcon});
	gmap.addOverlay(endMarker);
	$("#directions tbody").html("<tr><td colspan=4>1. START: " + $("#start").val() + "</td></tr>" +
		route.directions +
		"<tr><td>" + route.endStep + ". END: " + $("#end").val() + "</td>" +
		"<td>Total: " + route.totalDist + "</td>" + 
		"<td colspan=2 style='text-align: center'><a id='linkToDirs'>Link to directions</a></td></tr>");
	$("#directions").show();
	if (isIphone || isAndroid) {
		$("#directions").width(gmap.getSize().width);
		setTimeout(function() {
			window.scrollTo(0, $('#directions').attr('offsetTop'));
		}, 0);
	} else {
		$("#status").empty();
	}
	$("#debug").html("Found route in " + route.time + " seconds");
	$("#inputForm :input").attr("disabled", false);
	$("#linkToDirs").attr("href", BASEURL + "/?" + $("#inputForm").serialize());
	//updateStatus("done")
}

// show messages in console
function updateStatus(txt) {
	if (isIphone || isAndroid)
		$("#status").html(txt);
	else
		$("#status").append(txt + "<br>");
}

// convert GLatLng to lon,lat str (e.g. "-127.233,37.12") for bikemap
function gLatLngToStr(gLatLng) {
	return gLatLng.lng() + "," + gLatLng.lat()
}

// convert bike map (lon,lat) str to GLatLng
function strToGLatLng(strPt) {
	var latlong = strPt.split(',');
	var lat = latlong[1];
	var lon = latlong[0];
	return new GLatLng(parseFloat(lat), parseFloat(lon));
}

function getQueryValue(variable) {
	var pairs = window.location.search.replace(/^.*?\?/, "").split("&");
	for (var i in pairs) {
		var pair = pairs[i].split("=");
		if (decodeURIComponent(pair[0]) == variable)
			return decodeURIComponent(pair[1].replace(/\+/g, " "));
	}
	return null;
}
