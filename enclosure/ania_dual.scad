/* ANIA DUAL - millimetres. Source editable, OpenSCAD 2021.01.
   Nano 33 IoT dessous / Nano ESP32 dessus, composants vers +Z.
   Mesure utilisateur : 7 mm dessus-a-dessus, vide inter-cartes 5 mm.
   Verifier les fiches USB et le dessous des soudures avec le gabarit.
*/
part="assembly"; // [base,lid,layout,assembly,exploded,fit_test]
show_boards=false;
$fn=48;
L=60; W=36; H=26; wall=2.4; floor_t=2.4; lid_t=2.4;
pcb_l=43.18; pcb_w=17.78; pcb_t=2; pitch_z=7;
pcb_x=-27; pcb_bottom=8; pcb_upper_top=pcb_bottom+pcb_t+pitch_z;
fit=0.3; lid_clearance=0.4; usb_w=16.5; usb_floor=7;
// Hole centres: official Arduino drawings, 40.64 x 15.24, diameter 1.66.
holes=[for(x=[pcb_x+1.27,pcb_x+1.27+40.64],y=[-7.62,7.62]) [x,y]];
fixings=[for(x=[-25,25],y=[-13,13]) [x,y]];
assert(pcb_upper_top+5 < H-1,"Composants trop proches du couvercle");
assert(pcb_bottom-floor_t>=5,"Verifier les queues de broches sous la carte");
module outline(l=L,w=W,c=4){polygon([[-l/2+c,-w/2],[l/2-c,-w/2],[l/2,-w/2+c],[l/2,w/2-c],[l/2-c,w/2],[-l/2+c,w/2],[-l/2,w/2-c],[-l/2,-w/2+c]]);}
module prism(l,w,h,c=4){linear_extrude(h)outline(l,w,c);}
module outside(h){
 hull(){translate([0,0,0])linear_extrude(.01)outline(L-1.6,W-1.6,3.2);translate([0,0,.8])linear_extrude(.01)outline();}
 translate([0,0,.8])prism(L,W,h-1.6);
 hull(){translate([0,0,h-.8])linear_extrude(.01)outline();translate([0,0,h-.01])linear_extrude(.01)outline(L-1.6,W-1.6,3.2);}
}
module usb_cut(){translate([-L/2-1,-usb_w/2,usb_floor])cube([wall+3,usb_w,H+4]);}
module side_details(){
 // Shallow angled ribs: no sidewall perforation, no loose printed islands.
 for(side=[-1,1],x=[-13,-7,-1,5,11])
  translate([x,side*(W/2-.25),12])rotate([0,30,0])cube([1.2,1.0,13],center=true);
}
module base(){
 difference(){
  union(){
   difference(){outside(H);translate([0,0,floor_t])prism(L-2*wall,W-2*wall,H+1,2);usb_cut();side_details();}
   for(p=fixings)translate([p[0],p[1],floor_t-.1])cylinder(h=H-floor_t+.1,d=6);
   for(p=holes){
    translate([p[0],p[1],floor_t-.1])cylinder(h=pcb_bottom-floor_t+.1,d=3.2);
    translate([p[0],p[1],pcb_bottom-.1])cylinder(h=1.3,d=1.3);
   }
  }
  for(p=fixings)translate([p[0],p[1],H-8.5])cylinder(h=9,d=2.1);
 }
}
module slot2d(len=12,w=1.6){hull(){translate([0,-(len-w)/2])circle(d=w);translate([0,(len-w)/2])circle(d=w);}}
module lid(){ // Bottom surface at z=0; underside registration parts extend below.
 difference(){
  union(){
   hull(){linear_extrude(.01)outline();translate([0,0,lid_t-.01])linear_extrude(.01)outline(L-2,W-2,3);}
   // Registration skirt, clearance 0.30 mm per side.
   difference(){
    translate([0,0,-2])prism(L-2*wall-2*fit,W-2*wall-2*fit,2.1,1.8);
    translate([0,0,-2.1])prism(L-2*wall-2*fit-2.8,W-2*wall-2*fit-2.8,2.4,1.2);
    translate([-L/2-1,-usb_w/2-.4,-3])cube([wall+5,usb_w+.8,4]);
    for(p=fixings)translate([p[0],p[1],-3])cylinder(h=4,d=6.8);
   }
   // Vertical retainers stop 0.4 mm above upper PCB corner lands.
   for(p=holes)translate([p[0],p[1],-(H-pcb_upper_top-lid_clearance)])cylinder(h=H-pcb_upper_top-lid_clearance+.1,d=3.0);
  }
  for(p=fixings){translate([p[0],p[1],-3])cylinder(h=7,d=2.8);translate([p[0],p[1],lid_t-1.1])cylinder(h=2,d=5.4);}
  for(x=[-1,3,7,11,15])translate([x,0,-3])rotate([0,0,-25])linear_extrude(8)slot2d();
  translate([-13,0,lid_t-.6])linear_extrude(1)rotate([0,0,90])text("ANIA",size=5,halign="center",valign="center",font="Liberation Sans:style=Bold");
 }
}
module boards(){
 for(z=[pcb_bottom,pcb_bottom+pitch_z]){
  color([.05,.35,.35])difference(){translate([pcb_x,-pcb_w/2,z])cube([pcb_l,pcb_w,pcb_t]);for(p=holes)translate([p[0],p[1],z-.1])cylinder(h=pcb_t+.2,d=1.66);}
 }
 color("silver")translate([pcb_x-1.3,-4,pcb_bottom+pcb_t])cube([6,8,3]);
 color("silver")translate([pcb_x-1.3,-4.5,pcb_bottom+pitch_z+pcb_t])cube([7,9,3.5]);
 color([.5,.5,.5])translate([pcb_x+26,-6,pcb_upper_top])cube([12,12,3.8]);
}
module lid_print(){translate([0,0,lid_t])rotate([180,0,0])lid();}
module fit_test(){ // Lower section only, quick fit before a complete print.
 intersection(){base();translate([-L/2-1,-W/2-1,0])cube([L+2,W+2,pcb_bottom+1.3]);}
}
if(part=="base")base();
else if(part=="lid")lid_print();
else if(part=="fit_test")fit_test();
else if(part=="layout"){translate([0,-W/2-3,0])base();translate([0,W/2+3,0])lid_print();}
else if(part=="collision_boards"){intersection(){union(){base();translate([0,0,H])lid();}boards();}}
else if(part=="collision_lid"){intersection(){base();translate([0,0,H])lid();}}
else if(part=="exploded"){color([.12,.15,.19])base();if(show_boards)boards();translate([0,0,H+14])color([.05,.65,.62])lid();}
else {color([.12,.15,.19])base();if(show_boards)boards();translate([0,0,H])color([.05,.65,.62])lid();}
