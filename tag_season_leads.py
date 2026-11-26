#!/usr/bin/env python3
"""
Season-level leads: one card per design inside Winter and Summer.

winter-collection / summer-collection stay whole (108 / 167) because that is what the
discounts target. These extra tags drive *browsing* collections that show one card per
design, so the homepage rows don't repeat the same artwork three times.
"""
import json, os, sys, time, urllib.request, urllib.error

API="2026-07"
FAM={"Hoodie":"winter","Sweatshirt":"winter","Regular Fit T-Shirt":"summer",
     "Oversized Heavy Premium":"summer","Oversized Light-Soft":"summer"}

def gql_factory(shop, token):
    url=f"https://{shop}/admin/api/{API}/graphql.json"
    def gql(q,v=None):
        body=json.dumps({"query":q,"variables":v or {}}).encode()
        req=urllib.request.Request(url,data=body,headers={
            "X-Shopify-Access-Token":token,"Content-Type":"application/json"})
        for a in range(6):
            try:
                with urllib.request.urlopen(req) as r: out=json.load(r)
            except urllib.error.HTTPError as e:
                if e.code in (429,500,502,503): time.sleep(2*(a+1)); continue
                raise RuntimeError(f"HTTP {e.code}: {e.read()[:300].decode(errors='replace')}")
            if out.get("errors"):
                if "THROTTLED" in json.dumps(out["errors"]): time.sleep(3); continue
                raise RuntimeError(json.dumps(out["errors"])[:300])
            ts=out.get("extensions",{}).get("cost",{}).get("throttleStatus",{})
            if ts.get("currentlyAvailable",2000)<400: time.sleep(2)
            return out
        raise RuntimeError("retries exhausted")
    return gql

def main():
    groups=json.load(open("catalog-build/design_groups.json"))
    picks={}                      # handle -> tag
    for design, items in groups.items():
        for season in ("winter","summer"):
            inseason=[i for i in items if FAM.get(i["style"])==season]
            if inseason:
                inseason.sort(key=lambda x: float(x["price"]))
                picks[inseason[0]["handle"]]=f"lead-{season}"
    print(f"{len(picks)} season-lead products across {len(groups)} designs")

    shop,token=os.environ.get("SHOP"),os.environ.get("TOKEN")
    if not (shop and token): sys.exit("SHOP and TOKEN required")
    gql=gql_factory(shop,token)

    ids,cursor={},None
    while True:
        d=gql("query($c:String){products(first:250,after:$c){pageInfo{hasNextPage endCursor}nodes{id handle}}}",
              {"c":cursor})["data"]["products"]
        ids.update({n["handle"]:n["id"] for n in d["nodes"]})
        if not d["pageInfo"]["hasNextPage"]: break
        cursor=d["pageInfo"]["endCursor"]

    ok=miss=0
    M='mutation($id:ID!,$tags:[String!]!){ tagsAdd(id:$id,tags:$tags){ userErrors{message} } }'
    for i,(handle,tag) in enumerate(picks.items(),1):
        gid=ids.get(handle)
        if not gid: miss+=1; continue
        gql(M,{"id":gid,"tags":[tag]}); ok+=1
        if i%40==0: print(f"   {i}/{len(picks)}")
    print(f"tagged={ok} missing={miss}")

    CC='mutation($i:CollectionInput!){ collectionCreate(input:$i){ collection{id handle} userErrors{field message} } }'
    pubs=[n["id"] for n in gql("{publications(first:10){nodes{id name}}}")["data"]["publications"]["nodes"]
          if n["name"] in ("Online Store","Shop")]
    for season,title in (("winter","Winter Designs"),("summer","Summer Designs")):
        r=gql(CC,{"i":{"title":title,"handle":f"{season}-designs",
            "descriptionHtml":f"One card per design for {season} — the cheapest {season} garment leads.",
            "ruleSet":{"appliedDisjunctively":False,
                       "rules":[{"column":"TAG","relation":"EQUALS","condition":f"lead-{season}"}]}}})
        d=r["data"]["collectionCreate"]
        if d["userErrors"]:
            print(f"  {title}: {d['userErrors']}")
            cols={c['handle']:c['id'] for c in gql('{collections(first:40){nodes{handle id}}}')["data"]["collections"]["nodes"]}
            cid=cols.get(f"{season}-designs")
        else:
            cid=d["collection"]["id"]; print(f"  {title}: created")
        if cid:
            gql('mutation($id:ID!,$in:[PublicationInput!]!){ publishablePublish(id:$id,input:$in){ userErrors{message} } }',
                {"id":cid,"in":[{"publicationId":p} for p in pubs]})
            print(f"    published {season}-designs")

if __name__=="__main__": main()
