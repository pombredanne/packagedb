/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.lang.aspect.timer"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.lang.aspect.timer"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.lang.aspect.timer"] = true;
dojo.provide("dojox.lang.aspect.timer");

(function(){
	var aop = dojox.lang.aspect,
		uniqueNumber = 0;
	
	var Timer = function(name){
		this.name = name || ("DojoAopTimer #" + ++uniqueNumber);
		this.inCall = 0;
	};
	dojo.extend(Timer, {
		before: function(/*arguments*/){
			if(!(this.inCall++)){
				
			}
		},
		after: function(/*excp*/){
			if(!--this.inCall){
				
			}
		}
	});
	
	aop.timer = function(/*String?*/ name){
		// summary:
		//		Returns an object, which can be used to time calls to methods.
		//
		// name:
		//		The optional unique name of the timer.

		return new Timer(name);	// Object
	};
})();

}

}};});