#!/usr/bin/env python
# -*- coding: utf-8 -*-
# mf2 to jf2 converter
# licence cc0
#  2015 Kevin Marks

import logging


def flattenProperties(items):
    if type(items) is list:
        if len(items) <1:
            return {}
        if len(items)== 1:
            item = items[0]    
            if type(item) is dict:
                if item.has_key("type"):
                    props ={"type":item.get("type",["-"])[0].split("-")[1:][0]}
                    properties =  item.get("properties",{})
                    for prop in properties:
                        props[prop] = flattenProperties(properties[prop])
                    children  =  item.get("children",[])
                    if children:
                        if len(children) == 1:
                            props["children"] =[flattenProperties(children)]
                        else:
                            props["children"] =flattenProperties(children)["children"]
                    return props
               
                elif item.has_key("value"):
                    return item["value"]
                else:
                    return ''
            else:
                return item
        else:
            return {"children":[flattenProperties([child]) for child in items]}
    else:
        return items #not a list, so string
    

def mf2tojf2(mf2):
    """I'm going to have to recurse here"""
    jf2={}
    items = mf2.get("items",[])
    jf2=flattenProperties(items)
    #print jf2
    return jf2