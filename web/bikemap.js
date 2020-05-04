var themap = null;		 // global map object
var startAddy;         // start/end addresses
var endAddy;
var startGeoPt;        // geocoded start/end addresses
var endGeoPt;
var closestStartPt;    // closest matches to geocoded results in bike graph
var closestEndPt;
var gettingClosestPts; // poor man's synchronization mechanism

// see if they're on a sleek sexy phone
var agent=navigator.userAgent.toLowerCase();
var isIphone = (agent.indexOf('iphone')!=-1);
var isAndroid =  (agent.indexOf('android')!=-1);

var currentAddress = null; // if geolocation API is supported, cur. location
var BASEURL='http://amarpai.com/bikemap' // why is this the only thing I capitalized
var thegeocoder = new GClientGeocoder(); // why is this init'd in the middle of nowhere
  
/** 
  onLoad:
  0. init mobile, add event handlers, etc.
  1. populate form fields w/ preset values (greyed out)
  2. request user's location via geolocation API if present
  3. if location was present, reverse geocode to get approxmiate addy
     (TODO - offer 'my current location' option that uses lat/lng directly
      and shows user where they are on the map-- reverse geocoding loses precision)
  4. repopulate 'start' w/ current addy if it was found
**/

// onLoad
$(document).ready(function() {
  $.initMobile();
  
  // add onsubmit behavior for our form
  $("#inputform").submit(function() {
    geocodeStartAndEndPts(); 
    return false;
  });

  // if they passed in start/end address, go ahead and submit the form
  var startParam = $.getURLParam('start');
  var endParam =  $.getURLParam('end');
  var routePrefParam =$.getURLParam('routePref');
  var maxSlopeParam = $.getURLParam('maxSlope');
  if (startParam && endParam) {
    $('#start').attr('value',unescape(startParam));
    $('#end').attr('value',unescape(endParam));
    if (routePrefParam) {
      $('#routePref').attr('value', routePrefParam);
    } 
    if (maxSlopeParam) {
      $('#maxSlope').attr('value', maxSlopeParam);
    }
    geocodeStartAndEndPts();
  } else {
    formDefaultValues(); 
    //TODO(amarpai 7/6/2011) - something has gone screwy, getCurrentLocation may be involved
	//The app starts working due to 500 ISE caused by dijikstra not finding a path for inputs
	//Not sure what happened, maybe change in the geolocation API?  For now commenting this out.
    //getCurrentLocation(); 
  }
});

// TODO use jquery syntax for defining funcs, whatever it is

// 0. Do some tweaks for mobile
$.initMobile = function() {
  // scroll the urlbar out of sight on iPhone
  if (isIphone) {
    setTimeout(function() {window.scrollTo(0, 1);}, 0); 
  }
  if (isIphone || isAndroid) {
    // TODO just set a mobile class for body and have 
    // everything have a mobile derivative as needed
    $('#statustxt').addClass('mobile');
    $('#submitButton').addClass('mobile');
  }
}

// 1. Prepopulate form fields w/ greyed out entries that disappear on focus
// Taken from http://webdeveloper.beforeseven.com/
function formDefaultValues(fieldname) { 
  var active_color = '#000'; // Colour of user provided text
  var inactive_color = '#696969'; // Colour of default text
  if (fieldname) {
    var fields = [document.getElementById(fieldname)];
  } else {
    var fields = getElementsByClassName(document, "input", "default-value");
  }
  if (!fields) {
    return;
  }
  var default_values = new Array();
  for (var i = 0; i < fields.length; i++) {
    fields[i].style.color = inactive_color;
    if (!default_values[fields[i].id]) {
      default_values[fields[i].id] = fields[i].value;
    }
    fields[i].onfocus = function() {
      if (this.value == default_values[this.id]) {
        this.value = '';
        this.style.color = active_color;
      }
      this.onblur = function() {
        if (this.value == '') {
          this.style.color = inactive_color;
          this.value = default_values[this.id];
        }
      }
    }
  }
}

// 2. Get user location
function getCurrentLocation() {
  //alert('getCurrentLocation');
  if (navigator.geolocation && (!currentAddress)) {
    updateStatus("Requesting current location...");
    navigator.geolocation.getCurrentPosition(onCurrentPosition,onPositionError);
  }
}

// 2. Error handler
function onPositionError(error) {
  var msg = error.message;
  if ((error.code == 1) && isIphone) {
    msg += "<br><i>To reenable on iPhone, go to: Settings->General->Reset->Reset Location Warnings (hmm actually that doesn't seem to work... iPhone bug I think)";
  }
  updateStatus(msg);
}

// 3. Reverse geocode
function onCurrentPosition(position) {
  //alert('onCurrentPosition');
  if (!currentAddress) {
    lat=position.coords.latitude;
    lng=position.coords.longitude;
    accuracy=position.coords.accuracy;
    updateStatus("Lat:"+lat+","+ " Lon: " +lng + "<br/>Reverse geocoding...");
    latlng=new GLatLng(lat,lng);
    thegeocoder.getLocations(latlng, onReverseGeo);
  }
}

// 4. Update start location
// http://code.google.com/apis/maps/documentation/services.html#ReverseGeocoding
function onReverseGeo(response) {
  //alert('onReverseGeo');
  if (currentAddress) {
   return; 
  }
  if (response && response.Status.code == 200) {
    place = response.Placemark[0];
    currentAddress = place.address;
    if (currentAddress.indexOf('Francisco') != -1) {
      firstComma=currentAddress.indexOf(',');
      if (firstComma != -1) {
        currentAddress=currentAddress.substr(0,firstComma);
      }
      startfield=document.getElementById('start');
      if (startfield) {
        startfield.value=currentAddress;
        formDefaultValues('start');
      }
      updateStatus("Approximate address: " + currentAddress);
    } else {
      updateStatus("Approximate address: " + currentAddress + "<br>Not in San Francisco, ignoring");
    }
  } else {
    var msg = "Reverse geocode failed. " 
    if (response) {
      msg+="Response status=" + response.Status.code;
    } else {
      msg += "Response=null";
    }
    updateStatus(msg);
  }
}

  
/**
  onSubmit:
  1. geocode start & end points
  2. onGeocode, take the resulting GLatLon and find closest points in our bike graph
  3. onClosestPts, find a route from closest start to closest end pt
  4. onRoute, render overlay on the map and show directions
  
  A lot of this could/should happen simultaneously in a single request on backend, but
  my webhosting sucks.  So the client has to be the server, and I had to break up the
  process into steps that don't take too much time.
**/

// 1. Geocode start/end addresses
function geocodeStartAndEndPts()
{
  document.getElementById("statustxt").innerHTML = "";
	updateStatus("Geocoding addresses");	
	startAddy = $('#start').attr('value');
	endAddy = $('#end').attr('value');
  thegeocoder.getLatLng(startAddy+",San Francisco, CA",  onGeoCodeStart);
  thegeocoder.getLatLng(endAddy+",San Francisco, CA", onGeoCodeEnd);
  gettingClosestPts=null; // first one in gets to set
}

// 1. Response handler (base, then specialized cos I can't figure out
// how to create anonymous function w/ one open parameter above)
function onGeoCode(pt, glatlon) {
  if (! glatlon) {
    updateStatus("Error - address not found");
  } else {
    if (pt == 'start') {
      startGeoPt = glatlon;
    } else if (pt == 'end') {
      endGeoPt = glatlon;
    } else {
      updateStatus('Bad pt in onGeoCode: ' + pt);
    }
  }
  if (startGeoPt && endGeoPt && !gettingClosestPts) {
    gettingClosestPts=true;
    getClosestPtsInNetwork(startGeoPt, endGeoPt);
  }
}

// 1. handle geocode response for start addy
function onGeoCodeStart(glatlon) {
  return onGeoCode('start', glatlon);
}

// 1. handle geocode response for end addy
function onGeoCodeEnd(glatlon) {
  return onGeoCode('end', glatlon);
}

// 2. Find closest pts in bike graph
function getClosestPtsInNetwork(startGeoPt, endGeoPt) {
	updateStatus("Finding closest points in network");
 	var	url	= BASEURL+"/get_pt.py";
 	var args = {'start': gLatLonToStr(startGeoPt), "end": gLatLonToStr(endGeoPt)};
	// do we need to hold onto xhr handles?
	var xhr = $.get(url, args, onClosestPts);
}

// 2. Response handler
function onClosestPts(response, status) {
  if (status != 'success') { 
	  updateStatus("Problem retrieving data,	status=" + status);
  } else if (! response) {
    updateStatus("Error, null response");
  } else {
    var resultObj = eval('(' + response + ')');
  	if (resultObj.error == false) {
		  findRoute(resultObj);
		} else {
			updateStatus("Error in get_pt: " + resultObj.msg);
		}
  }
}

// 3. Compute path
function findRoute(resultObj)
{
	//alert('findRoute');
	updateStatus("Calculating route (may be slow...)");
	var	maxSlope = document.getElementById('maxSlope').value;
	var routePref = document.getElementById('routePref').value;
	// store gLatLon representations of start/end pts in bike graph, so
	// we can draw start/end markers later.  could probably name these better.
	closestStartPt = strToGLatLng(resultObj.startPt);
	closestEndPt = strToGLatLng(resultObj.endPt);
  var url = BASEURL + '/find_path.py';
  var args = {'start':resultObj.startPt, 'end':resultObj.endPt, 
              'maxSlope':maxSlope, 'routePref':routePref};  
 	var xhr = $.get(url, args, onRoute);
}

// 3. Response handler
// TODO abstract response handling into one function, use closure
// to bind particulars of success handling
function onRoute(response, status) {
  if (status != 'success') { 
	  updateStatus("Problem retrieving data,	status=" + status);
  } else if (! response) {
    updateStatus("Error, null response");
  } else {
    var resultObj = eval('(' + response + ')');
  	if (resultObj.error == false) {
		  renderRoute(resultObj);
		} else {
			updateStatus("Error in find_route: " + resultObj.msg);
		}
  }
}

// 4. Draw map & show directions
function renderRoute(resultObj)
{
	updateStatus("Rendering route...");
	var points = []; // array of GLatLng 
  var latlngbounds = new GLatLngBounds();
	for (var i = 0; i < resultObj.points.length; i++) {
		var latlong = []
		var point = strToGLatLng(resultObj.points[i]);
		points.push(point);
    latlngbounds.extend( point );
	} 
	var ourwidth;
  var ourheight;
  if (isIphone || isAndroid) {
    // 320x356 portrait, 408x208 landscape
	  ourwidth= "400px";
    ourheight="300px";
  } else {
    ourwidth = "800px";
    ourheight="500px";
  }
  var mapContainer = document.getElementById('gmap');
  mapContainer.style.display = 'block'; 
  mapContainer.style.width =ourwidth;
  mapContainer.style.height=ourheight;
	themap = new GMap2(document.getElementById("gmap"));
	themap.setCenter( latlngbounds.getCenter( ), themap.getBoundsZoomLevel( latlngbounds ) );
  //themap.setUIToDefault();
	var uiOptions = themap.getDefaultUI();
	uiOptions.zoom.scrollwheel=false;
	if (isIphone || isAndroid) {
	  uiOptions.keyboard=false;
	  uiOptions.zoom.doubleclick=false;
  }
  themap.setUI(uiOptions);
  themap.addOverlay( new GPolyline( points, "	#0000FF",4,.75 ) );
  
  // add start and end points
  var greenIcon = new GIcon(G_DEFAULT_ICON);
  greenIcon.image = "http://www.google.com/mapfiles/dd-start.png";
  var redIcon = new GIcon(G_DEFAULT_ICON);
  redIcon.image = "http://www.google.com/mapfiles/dd-end.png";
  var startMarker = new GMarker(closestStartPt, 
    { clickable:false, draggable: false, title:'Start: ' + startAddy, icon:greenIcon});
  var endMarker = new GMarker(closestEndPt, 
    {clickable:false, draggable: false, title:'End: ' + endAddy, icon:redIcon}); 
  themap.addOverlay(startMarker);
  themap.addOverlay(endMarker);
  
  if  (isIphone || isAndroid) {
	  var finalDirs = "<table width='"+themap.getSize().width+"px' border=1 cellpadding = 1 cellspacing=1 id='directionsTable'><tr><td>Directions<td>Distance<td>Steepest climb<td>Street type<\/tr>"
  } else {
    var finalDirs = "<table border=1 cellpadding = 1 cellspacing=1 id='directionsTable'><tr><td>Directions<td>Distance<td>Steepest climb<td>Street type<\/tr>"
  }
  var linkToDirs=BASEURL+"?start="+escape(startAddy)+"&end="+escape(endAddy)+"&routePref="+escape($('#routePref').attr('value'))+"&maxSlope="+escape($('#maxSlope').attr('value'));
  //alert(linkToDirs);
	finalDirs += "<tr><td>1. START: " + document.getElementById("start").value + "<\/tr>"
	finalDirs += resultObj.directions;
	finalDirs += "<tr><td>" + resultObj.endStep + ". " + "END: " + 
	  document.getElementById("end").value + "<td>Total: " + resultObj.totalDist +
	   "<td colspan=2><a href='" + linkToDirs + "'>Link to directions</a><\/tr>";
	finalDirs += "<\/table><p>";
	//updateStatus("setting final dirs etc")
	if (isIphone || isAndroid) {
	  document.getElementById("directions").style.display = "block";
	  document.getElementById("directions").innerHTML = finalDirs;
	  setTimeout(function() {
	    window.scrollTo(0,document.getElementById('directions').offsetTop); 
    }, 0);
  } else {
    document.getElementById("statustxt").innerHTML = finalDirs;
  }
	document.getElementById("debug").innerHTML = "Found route in : " + resultObj.time + " seconds";
	//updateStatus("done")
	//alert('done')
}

/***********
 HELPER FUNCTIONS THAT SIT AROUND HELPIN' AND SHIT
 ************/

// show messages in console
function updateStatus(txt)
{
  if (isIphone || isAndroid) {
	  document.getElementById("statustxt").innerHTML = txt;
  } else {
	  document.getElementById("statustxt").innerHTML +=  txt + "<br>";
	}
}

// convert GLatLon to lon,lat str (e.g. "-127.233,37.12") for bikemap
function gLatLonToStr(gLatLon) {
  return gLatLon.lng() + "," + gLatLon.lat()
}

// convert bike map (lon,lat) str to GLatLng
function strToGLatLng(strPt) {
  latlong = strPt.split(',');
	lat = latlong[1];
	lon = latlong[0]; 
	//alert('point ' + i + " is " + latlong);
	return new GLatLng(parseFloat(lat), parseFloat(lon));
}

// TODO replace w/ jQuery 
// Written by Jonathan Snook, http://www.snook.ca/jonathan
// Add-ons by Robert Nyman, http://www.robertnyman.com
function getElementsByClassName(oElm, strTagName, strClassName){
  var arrElements = (strTagName == "*" && oElm.all)? oElm.all : oElm.getElementsByTagName(strTagName);
  var arrReturnElements = new Array();
  strClassName = strClassName.replace(/\-/g, "\\-");
  var oRegExp = new RegExp("(^|\\s)" + strClassName + "(\\s|$)");
  var oElement;
  for (var i = 0; i < arrElements.length; i++) {
    oElement = arrElements[i];
    if (oRegExp.test(oElement.className)) {
      arrReturnElements.push(oElement);
    }
  }
  return (arrReturnElements);
}

/** Copyright (c) 2006 Mathias Bank (http://www.mathias-bank.de) 
    Returns get parameters.
    If the desired param does not exist, null will be returned
    @example value = $.getURLParam("paramName");
**/ 
$.getURLParam = function(strParamName) {
	var strReturn = "";
  var strHref = window.location.href;
  var bFound=false;
  
  var cmpstring = strParamName + "=";
  var cmplen = cmpstring.length;

  if ( strHref.indexOf("?") > -1 ){
    var strQueryString = strHref.substr(strHref.indexOf("?")+1);
    var aQueryString = strQueryString.split("&");
    for ( var iParam = 0; iParam < aQueryString.length; iParam++ ){
      if (aQueryString[iParam].substr(0,cmplen)==cmpstring){
        var aParam = aQueryString[iParam].split("=");
        strReturn = aParam[1];
        bFound=true;
        break;
      }
      
    }
  }
  if (bFound==false) return null;
  return strReturn;
}



