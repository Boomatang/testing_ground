//! By convention, main.zig is where your main function lives in the case that
//! you are building an executable. If you are making a library, the convention
//! is to delete this file and start with root.zig instead.

const std = @import("std");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const stdout_file = std.io.getStdOut().writer();
    var bw = std.io.bufferedWriter(stdout_file);
    const stdout = bw.writer();

    const Result = struct { language: []const u8, format: []const u8, time: i128, cores: usize, sample: u64, pi: f64 };

    const args = try std.process.argsAlloc(allocator);
    defer std.process.argsFree(allocator, args);

    if (args.len != 3) {
        std.debug.print("Usage: {s} single|multi <interger>\n", .{args[0]});
        std.debug.print("Example: {s} single 42\n", .{args[0]});
    }

    const command_str = args[1];

    const input_str = args[2];
    const number = std.fmt.parseInt(u64, input_str, 10) catch |err| {
        switch (err) {
            error.InvalidCharacter => {
                std.debug.print("Bad thing", .{});
                return;
            },
            error.Overflow => {
                std.debug.print("number to big", .{});
                return;
            },
        }
    };

    if (std.mem.eql(u8, command_str, "single")) {
        const start = std.time.nanoTimestamp();
        const result = try monte_carlo_pi(number);
        const end = std.time.nanoTimestamp() - start;

        const data = Result{
            .language = "zig",
            .format = "single threaded",
            .cores = 1,
            .sample = number,
            .pi = result,
            .time = end,
        };
        const json_string = try std.json.stringifyAlloc(allocator, data, .{});
        defer allocator.free(json_string);

        try stdout.print("{s}\n", .{json_string});
    }

    if (std.mem.eql(u8, command_str, "multi")) {
        const cores = try std.Thread.getCpuCount();

        const start = std.time.nanoTimestamp();
        const result = try monte_carlo_pi_threaded(number, cores, allocator);
        const end = std.time.nanoTimestamp() - start;

        const data = Result{
            .language = "zig",
            .format = "multi threaded",
            .cores = cores,
            .sample = number,
            .pi = result,
            .time = end,
        };
        const json_string = try std.json.stringifyAlloc(allocator, data, .{});
        defer allocator.free(json_string);

        try stdout.print("{s}\n", .{json_string});
    }
    try bw.flush(); // Don't forget to flush!

}

fn monte_carlo_pi(nsample: u64) !f64 {
    var acc: f64 = 0;
    var i: i32 = 1;

    var prng = std.Random.DefaultPrng.init(blk: {
        var seed: u64 = undefined;
        try std.posix.getrandom(std.mem.asBytes(&seed));
        break :blk seed;
    });
    const rand = prng.random();

    while (i <= nsample) : (i += 1) {
        const x = rand.float(f32) * 2.0 - 1.0;
        const y = rand.float(f32) * 2.0 - 1.0;
        if ((x * x + y * y) <= 1.0) {
            acc += 1;
        }
    }
    const n: f64 = @floatFromInt(nsample);
    const result = 4.0 * acc / n;
    return result;
}

const WorkerData = struct {
    block: u64,
    acc: *f64,
    mutex: *std.Thread.Mutex,
};

fn worker(data: *WorkerData) !void {
    var i: i32 = 1;
    var acc: f64 = 0;
    var prng = std.Random.DefaultPrng.init(blk: {
        var seed: u64 = undefined;
        try std.posix.getrandom(std.mem.asBytes(&seed));
        break :blk seed;
    });
    const rand = prng.random();

    while (i <= data.block) : (i += 1) {
        const x = rand.float(f32) * 2.0 - 1.0;
        const y = rand.float(f32) * 2.0 - 1.0;
        if ((x * x + y * y) <= 1.0) {
            acc += 1;
        }
    }
    data.mutex.lock();
    data.acc.* += acc;
    data.mutex.unlock();
}

fn monte_carlo_pi_threaded(nsample: u64, cores: usize, alloc: std.mem.Allocator) !f64 {
    const block_size = nsample / cores;

    var acc: f64 = 0;
    var mutex = std.Thread.Mutex{};

    var threads = try alloc.alloc(std.Thread, cores);
    defer alloc.free(threads);

    var worker_data = try alloc.alloc(WorkerData, cores);
    defer alloc.free(worker_data);

    for (0..cores) |i| {
        worker_data[i] = WorkerData{
            .acc = &acc,
            .mutex = &mutex,
            .block = block_size,
        };

        threads[i] = try std.Thread.spawn(.{}, worker, .{&worker_data[i]});
    }

    for (threads) |thread| {
        thread.join();
    }

    const n: f64 = @floatFromInt(nsample);
    const result = 4.0 * acc / n;
    return result;
}
