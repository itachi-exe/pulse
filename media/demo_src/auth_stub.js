(()=>{const of=window.fetch;window.fetch=async(u,o)=>{u=String(u);
if(u.includes('/auth/me'))return new Response(JSON.stringify({email:'demo@pulse.dev',name:'Demo'}),{status:200});
if(u.includes('/auth/keys'))return new Response(JSON.stringify({keys:[]}),{status:200});
if(u.includes('/auth/categories')){const c=await (await of('/data/categories')).json();
 for(const k in c)c[k].enabled=['crypto','regulatory','politics','news'].includes(k);
 return new Response(JSON.stringify(c),{status:200});}
return of(u,o);};})();