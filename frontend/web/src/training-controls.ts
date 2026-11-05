/** One plate step is 0.2 virtual load, with the Python protocol's finite bounds. */
export function adjustWeight(current:number,direction:1|-1):number{
  if(!Number.isFinite(current)||current<.1||current>3)throw new Error("Invalid equipment weight");
  return Math.max(.1,Math.min(3,Math.round((current+direction*.2)*100)/100));
}
