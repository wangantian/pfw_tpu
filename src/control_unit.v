/*
 * Copyright (c) 2025 PFW Tiny Tapeout Team
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module control_unit (
    input wire clk,
    input wire rst,
    input wire load_en,

    output reg [2:0] mem_addr,

    output reg mmu_en,
    output reg [2:0] mmu_cycle,

    output wire [1:0] state_out
);

    localparam [1:0] S_IDLE = 2'b00;
    localparam [1:0] S_LOAD_MATS = 2'b01;
    localparam [1:0] S_MMU_FEED_COMPUTE_WB = 2'b10;

    reg [1:0] state, next_state;

    assign state_out = state;

    always @(*) begin
        next_state = state;

        case (state)
            S_IDLE: begin
                if (load_en) begin
                    next_state = S_LOAD_MATS;
                end
            end

            S_LOAD_MATS: begin
                if (mem_addr == 3'b111) begin
                    next_state = S_MMU_FEED_COMPUTE_WB;
                end
            end

            S_MMU_FEED_COMPUTE_WB:
                next_state = S_MMU_FEED_COMPUTE_WB;

            default: begin
                next_state = S_IDLE;
            end
        endcase
    end

    always @(posedge clk) begin
        if (rst) begin
            state <= S_IDLE;
            mmu_cycle <= 0;
            mmu_en <= 0;
            mem_addr <= 0;
        end else begin
            state <= next_state;
            mem_addr <= 0;
            case (state)
                S_IDLE: begin
                    mmu_cycle <= 0;
                    mmu_en <= 0;
                    if (load_en) begin
                        mem_addr <= mem_addr + 1;
                    end
                end

                S_LOAD_MATS: begin
                    if (load_en) begin
                        mem_addr <= mem_addr + 1;
                    end

                    if (mem_addr == 3'b101) begin
                        mmu_en <= 1;
                    end else if (mem_addr >= 3'b110) begin
                        mmu_en <= 1;
                        mmu_cycle <= mmu_cycle + 1;
                        if (mem_addr == 3'b111) begin
                            mem_addr <= 0;
                        end
                    end
                end

                S_MMU_FEED_COMPUTE_WB: begin
                    if (load_en) begin
                        mem_addr <= mem_addr + 1;
                    end
                    mmu_cycle <= mmu_cycle + 1;
                    if (mmu_cycle == 3'b111) begin
                        mmu_cycle <= 0;
                    end else if (mmu_cycle == 1) begin
                        mem_addr <= 0;
                    end
                end

                default: begin
                    mmu_cycle <= 0;
                    mmu_en <= 0;
                end
            endcase
        end
    end

endmodule
