const fs=require('fs'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'../../extensions/escrs-assistant/adapter.js'),'utf8');
fs.writeFileSync(path.join(__dirname,'../src/adapter-source.js'),'// Generated from the canonical ESCRS adapter. Run npm run sync-adapter.\nexport default '+JSON.stringify(source)+';\n');
