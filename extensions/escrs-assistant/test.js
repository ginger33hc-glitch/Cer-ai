"use strict";
document.getElementById("test").addEventListener("click",async()=>{
  const button=document.getElementById("test"),status=document.getElementById("status");
  button.disabled=true;
  try {
    const result=await chrome.runtime.sendMessage({action:"SELF_TEST"});
    if(!result?.ok) throw new Error("Test açılamadı / Could not open test.");
    status.textContent="ESCRS açıldı. Alan kontrolünün tamamlanmasını bekleyin / Wait for field verification.";
  } catch(error){status.textContent=error.message;}
  finally{button.disabled=false;}
});
