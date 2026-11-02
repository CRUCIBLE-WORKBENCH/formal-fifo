// Independent shift-queue model. Acceptance uses its own count, never DUT flags.
reg f_past_valid=0;
reg [2:0] f_count;
reg [7:0] f_queue[0:3];
reg f_valid;
reg [7:0] f_data;
reg f_seen_full;
reg [3:0] f_writes;
reg [3:0] f_reads;
wire f_push=wr_en && (f_count<4);
wire f_pop=rd_en && (f_count>0);
integer f_i;
always @(posedge clk) begin
    f_past_valid<=1;
    if(!f_past_valid) assume(rst);
    if(f_past_valid) begin
        a_capacity: assert(level<=4);
        a_level: assert(level==f_count);
        a_full: assert(full==(f_count==4));
        a_empty: assert(empty==(f_count==0));
        a_valid: assert(rd_valid==f_valid);
        a_data: assert(rd_data==f_data);
        // Relational lemmas strengthen induction without assuming DUT behaviour.
        a_pointers: assert(wptr==((rptr+f_count)&3));
        for(f_i=0;f_i<4;f_i=f_i+1)
            if(f_i<f_count)
                assert(mem[(rptr+f_i)&3]==f_queue[f_i]);
        c_empty: cover(!rst && f_count==0);
        c_full: cover(!rst && f_count==4);
        c_simultaneous: cover(!rst && f_push && f_pop);
        c_full_to_empty: cover(!rst && f_seen_full && f_count==0);
        c_wrap: cover(!rst && f_writes==5);
        c_read_wrap: cover(!rst && f_reads==5);
        c_reset_active: cover(rst && f_count>0);
        c_full_write_rejected: cover(!rst && f_count==4 && wr_en && !rd_en);
        c_empty_read_rejected: cover(!rst && f_count==0 && rd_en && !wr_en);
        c_empty_both: cover(!rst && f_count==0 && rd_en && wr_en);
        c_full_both: cover(!rst && f_count==4 && rd_en && wr_en);
        c_nonzero_data: cover(!rst && rd_valid && rd_data==8'ha5);
    end
    if(rst) begin
        f_count<=0;f_valid<=0;f_data<=0;f_seen_full<=0;f_writes<=0;f_reads<=0;
    end else begin
        f_valid<=f_pop;
        if(f_pop) begin
            f_data<=f_queue[0];
            for(f_i=0;f_i<3;f_i=f_i+1) f_queue[f_i]<=f_queue[f_i+1];
        end
        if(f_push) f_queue[f_count-f_pop]<=wr_data;
        case({f_push,f_pop})
            2'b10:f_count<=f_count+1'b1;
            2'b01:f_count<=f_count-1'b1;
            default:begin end
        endcase
        if(f_count==4)f_seen_full<=1;
        if(f_push && f_writes<5)f_writes<=f_writes+1'b1;
        if(f_pop && f_reads<5)f_reads<=f_reads+1'b1;
    end
end
