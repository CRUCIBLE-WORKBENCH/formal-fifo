`timescale 1ns/1ps
module tb;
reg clk=0,rst=0,wr_en=0,rd_en=0;
reg [7:0] wr_data=0;
wire full,empty,rd_valid;
wire [2:0] level;
wire [7:0] rd_data;
fifo dut(.clk(clk),.rst(rst),.wr_en(wr_en),.rd_en(rd_en),.wr_data(wr_data),
         .full(full),.empty(empty),.level(level),.rd_valid(rd_valid),.rd_data(rd_data));
always #5 clk=~clk;
reg [7:0] queue[0:3];
integer count=0,cycles=0,checks=0,i,j,replay_count;
integer pushes=0,pops=0,both=0,rejected_writes=0,rejected_reads=0,resets=0;
reg expected_valid=0;
reg [7:0] expected_data=0;
reg [31:0] random_state=32'h52c0f1e1;
reg [10:0] replay[0:63];
task check;
input condition;
input [255:0] label;
begin
    checks=checks+1;
    if(condition !== 1'b1)
        $fatal(1,"FIFO_SIM_MISMATCH %0s cycle=%0d level=%0d expected=%0d rst=%b wr=%b rd=%b",label,cycles,level,count,rst,wr_en,rd_en);
end
endtask
task step;
input reset_request,write_request,read_request;
input [7:0] byte_value;
integer old_count;
reg push,pop;
begin
    @(negedge clk);rst=reset_request;wr_en=write_request;rd_en=read_request;wr_data=byte_value;
    old_count=count;
    push=write_request && old_count<4;
    pop=read_request && old_count>0;
    if(reset_request)begin
        count=0;expected_valid=0;expected_data=0;resets=resets+1;
    end else begin
        expected_valid=pop;
        if(pop)begin
            expected_data=queue[0];
            for(j=0;j<3;j=j+1)queue[j]=queue[j+1];
            pops=pops+1;
        end
        if(push)begin queue[old_count-pop]=byte_value;pushes=pushes+1;end
        count=old_count+push-pop;
        if(push && pop)both=both+1;
        if(write_request && !push)rejected_writes=rejected_writes+1;
        if(read_request && !pop)rejected_reads=rejected_reads+1;
    end
    @(posedge clk);#1;
    check(level===count,"occupancy");check(full===(count==4),"full");
    check(empty===(count==0),"empty");check(rd_valid===expected_valid,"read valid");
    check(rd_data===expected_data,"ordered/held read data");check(level<=4,"capacity");
    cycles=cycles+1;
end
endtask
initial begin
    if($test$plusargs("REPLAY"))begin
        if(!$value$plusargs("REPLAY_COUNT=%d",replay_count))$fatal(1,"REPLAY_COUNT_MISSING");
        if(replay_count<3 || replay_count>64)$fatal(1,"REPLAY_COUNT_INVALID");
        $readmemh("build/replay.mem",replay,0,replay_count-1);
        for(i=0;i<replay_count;i=i+1)step(replay[i][10],replay[i][9],replay[i][8],replay[i][7:0]);
        $display("FIFO_REPLAY_PASS cycles=%0d checks=%0d",cycles,checks);$finish;
    end
    step(1,0,0,0);
    step(0,0,1,0); // rejected empty read
    step(0,1,0,8'ha5);
    step(0,1,1,8'h3c); // simultaneous accepted transfers: occupancy remains one
    step(0,0,1,0);step(0,0,0,0);
    step(1,1,1,8'hff);
    for(i=0;i<4;i=i+1)step(0,1,0,i*8'h55);
    step(0,1,0,8'hff); // full write rejected
    step(0,1,1,8'h00); // full read accepted; concurrent write rejected
    repeat(4)step(0,0,1,0);
    step(0,1,1,8'hff); // empty write accepted; concurrent read rejected
    step(1,0,0,0); // reset while data was queued
    for(i=0;i<32;i=i+1)begin
        step(0,1,0,i);step(0,1,0,~i);step(0,0,1,0);step(0,0,1,0);
    end
    for(i=0;i<2048;i=i+1)begin
        random_state=random_state^(random_state<<13);
        random_state=random_state^(random_state>>17);
        random_state=random_state^(random_state<<5);
        step(i%257==128,random_state[0],random_state[1],random_state[15:8]);
    end
    $display("FIFO_SIM_PASS cycles=%0d checks=%0d pushes=%0d pops=%0d simultaneous=%0d rejected_writes=%0d rejected_reads=%0d resets=%0d",cycles,checks,pushes,pops,both,rejected_writes,rejected_reads,resets);$finish;
end
initial begin #1000000;$fatal(1,"SIMULATION_WATCHDOG");end
endmodule
