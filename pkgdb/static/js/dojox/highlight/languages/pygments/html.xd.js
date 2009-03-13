/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.highlight.languages.pygments.html"],
["require", "dojox.highlight._base"],
["require", "dojox.highlight.languages.pygments._html"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.highlight.languages.pygments.html"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.highlight.languages.pygments.html"] = true;
dojo.provide("dojox.highlight.languages.pygments.html");

dojo.require("dojox.highlight._base");
dojo.require("dojox.highlight.languages.pygments._html");

(function(){
	var dh = dojox.highlight, dhl = dh.languages, tags = [],
		ht = dhl.pygments._html.tags;
	
	for(var key in ht){
		tags.push(key);
	}
	tags = "\\b(" + tags.join("|") + ")\\b";
	
	dhl.html = {
		case_insensitive: true,
		defaultMode: {
			contains: [
				"name entity",
				"comment", "comment preproc",
				"_script", "_style", "_tag"
			]
		},
		modes: [
			// comments
			{
				className: "comment",
				begin: "<!--", end: "-->"
			},
			{
				className: "comment preproc",
				begin: "\\<\\!\\[CDATA\\[", end: "\\]\\]\\>"
			},
			{
				className: "comment preproc",
				begin: "\\<\\!", end: "\\>"
			},

			// strings
			{
				className: "string",
				begin: "'", end: "'",
				illegal: "\\n",
				relevance: 0
			},
			{
				className: "string",
				begin: '"', 
				end: '"',
				illegal: "\\n",
				relevance: 0
			},
			
			// names
			{
				className: "name entity",
				begin: "\\&[a-z]+;", end: "^"
			},
			{
				className: "name tag",
				begin: tags, end: "^",
				relevance: 5
			},
			{
				className: "name attribute",
				begin: "\\b[a-z0-9_\\:\\-]+\\s*=", end: "^",
				relevance: 0
			},
			
			{
				className: "_script",
				begin: "\\<script\\b", end: "\\</script\\>",
				relevance: 5
			},
			{
				className: "_style",
				begin: "\\<style\\b", end: "\\</style\\>",
				relevance: 5
			},
			
			{
				className: "_tag",
				begin: "\\<(?!/)", end: "\\>",
				contains: ["name tag", "name attribute", "string", "_value"]
			},
			{
				className: "_tag",
				begin: "\\</", end: "\\>",
				contains: ["name tag"]
			},
			{
				className: "_value",
				begin: "[^\\s\\>]+", end: "^"
			}
		]
	};
})();

}

}};});