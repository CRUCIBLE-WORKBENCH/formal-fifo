// Four-entry, eight-bit synchronous FIFO with registered read response.
module fifo (
    input wire clk,rst,wr_en,rd_en,
    input wire [7:0] wr_data,
    output wire full,empty,
    output reg [2:0] level,
    output reg rd_valid,
    output reg [7:0] rd_data
);
    reg [7:0] mem[0:3];
    reg [1:0] wptr,rptr;
    wire take_write=wr_en && !full;
    wire take_read=rd_en && !empty;
    assign full=(level==4);
    assign empty=(level==0);
    always @(posedge clk) begin
        if(rst) begin
            wptr<=0;rptr<=0;level<=0;rd_valid<=0;rd_data<=0;
        end else begin
            rd_valid<=take_read;
            if(take_write) begin mem[wptr]<=wr_data;wptr<=wptr+1'b1;end
            if(take_read) begin rd_data<=mem[rptr];rptr<=rptr+1'b1;end
            case({take_write,take_read})
                2'b10:level<=level+1'b1;
                2'b01:level<=level-1'b1;
                default:begin end
            endcase
        end
    end
`ifdef FORMAL
`include "contract.vh"
`endif
endmodule
