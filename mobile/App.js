import React, {useRef,useState,useEffect} from 'react';
import {AppState,BackHandler,Button,Linking,Modal,StyleSheet,Text,View} from 'react-native';
import {SafeAreaProvider,SafeAreaView} from 'react-native-safe-area-context';
import {WebView} from 'react-native-webview';
import adapterSource from './src/adapter-source';
const {CERAI,ESCRS,trustedCerai,trustedEscrs,parseRequest,bridge,responseScript,transferScript}=require('./src/transport.cjs');

export default function App(){
  const main=useRef(null),destination=useRef(null),canGoBack=useRef(false);
  const [transfer,setTransfer]=useState(null),[status,setStatus]=useState(''),[mainError,setMainError]=useState(''),[hidden,setHidden]=useState(false);
  useEffect(()=>{const sub=AppState.addEventListener('change',s=>setHidden(s!=='active'));return()=>sub.remove();},[]);
  useEffect(()=>{const sub=BackHandler.addEventListener('hardwareBackPress',()=>{if(transfer){setTransfer(null);return true;}if(canGoBack.current){main.current?.goBack();return true;}return false;});return()=>sub.remove();},[transfer]);
  useEffect(()=>{if(!transfer)return;const timer=setTimeout(()=>{setTransfer(null);setMainError('Aktarım oturumu sona erdi / Transfer session expired.');},600000);return()=>clearTimeout(timer);},[transfer?.id]);
  function receive(event){
    const request=parseRequest(event.nativeEvent.data,event.nativeEvent.url);if(!request)return;
    if(request.action==='PING'){main.current?.injectJavaScript(responseScript(request.id,{ok:true,version:1,platform:'mobile'}));return;}
    if(transfer){main.current?.injectJavaScript(responseScript(request.id,{ok:false,error:'Close the current ESCRS session before a new transfer.'}));return;}
    main.current?.injectJavaScript(responseScript(request.id,{ok:true}));
    setStatus('ESCRS alanları doldurulup kontrol ediliyor / Filling and checking ESCRS fields…');
    setTransfer({id:request.id,payload:request.payload});
  }
  function inject(){if(transfer)destination.current?.injectJavaScript(transferScript(adapterSource,transfer.payload,transfer.id));}
  function receiveStatus(event){
    if(!trustedEscrs(event.nativeEvent.url) || event.nativeEvent.data.length>2000)return;
    let m;try{m=JSON.parse(event.nativeEvent.data);}catch{return;}
    if(m.channel!=='CERAI_MOBILE_STATUS' || m.id!==transfer?.id)return;
    setStatus(m.ok?'Aktarım kontrol edildi. Değerleri, lens sabitlerini ve PCA yöntemini gözden geçirip hesaplayın. / Transfer checked. Review values, constants and PCA before calculating.':'Aktarım eksik; henüz hesaplamayın / Transfer incomplete: '+m.error);
  }
  function external(url){try{const u=new URL(url);if(['https:','mailto:','tel:'].includes(u.protocol))Linking.openURL(url).catch(()=>setMainError('Bağlantı açılamadı / Could not open link.'));}catch{}}
  return <SafeAreaProvider><SafeAreaView style={styles.screen}>
    <View style={styles.header}><Text style={styles.title}>CER-AI</Text><Text>Mobil doğrulama sürümü / Mobile validation build</Text></View>
    {!!mainError&&<View><Text accessibilityRole="alert">{mainError}</Text><Button title="Yenile / Reload" onPress={()=>{setMainError('');main.current?.reload();}}/></View>}
    <WebView ref={main} source={{uri:CERAI+'/iol'}} style={styles.web} originWhitelist={['https://cer-ai.com','https://www.cer-ai.com']}
      onShouldStartLoadWithRequest={r=>trustedCerai(r.url)} onMessage={receive} injectedJavaScript={bridge}
      injectedJavaScriptForMainFrameOnly onLoadEnd={()=>main.current?.injectJavaScript(bridge)}
      onNavigationStateChange={n=>{canGoBack.current=n.canGoBack;}} onOpenWindow={e=>external(e.nativeEvent.targetUrl)}
      onError={()=>setMainError('CER-AI açılamadı. Bağlantıyı kontrol edin / Check your connection.')}
      javaScriptEnabled domStorageEnabled sharedCookiesEnabled mixedContentMode="never" allowFileAccess={false} />
    <Modal visible={!!transfer} animationType="slide" onRequestClose={()=>setTransfer(null)}>
      <SafeAreaView style={styles.screen}><View style={styles.header}><Text accessibilityRole="alert">{status}</Text>
        <View style={styles.buttons}><Button title="Yeniden dene / Retry" onPress={inject}/><Button title="CER-AI’ye dön / Back" onPress={()=>setTransfer(null)}/></View></View>
        {!!transfer&&<WebView key={transfer.id} ref={destination} source={{uri:ESCRS}} style={styles.web}
          originWhitelist={['https://iolcalculator.escrs.org']} onShouldStartLoadWithRequest={r=>trustedEscrs(r.url)}
          onLoadEnd={inject} onMessage={receiveStatus} incognito javaScriptEnabled domStorageEnabled
          onOpenWindow={e=>external(e.nativeEvent.targetUrl)} mixedContentMode="never" allowFileAccess={false}
          onError={()=>setStatus('ESCRS açılamadı / ESCRS could not load.')}/>}
        {hidden&&<View style={styles.cover}><Text>CER-AI</Text></View>}
      </SafeAreaView>
    </Modal>
    {hidden&&<View style={styles.cover}><Text>CER-AI</Text></View>}
  </SafeAreaView></SafeAreaProvider>;
}
const styles=StyleSheet.create({screen:{flex:1,backgroundColor:'#fff'},web:{flex:1},header:{padding:10,gap:6,backgroundColor:'#eaf0f6'},title:{fontSize:20,fontWeight:'700'},buttons:{flexDirection:'row',justifyContent:'space-between'},cover:{...StyleSheet.absoluteFillObject,backgroundColor:'#fff',alignItems:'center',justifyContent:'center'}});
