# Atomic sliding-window rate limit check + record, in one Redis round-trip.
#
# KEYS[1] = the rate-limit key
# ARGV[1] = current timestamp (float seconds)
# ARGV[2] = window size in seconds
# ARGV[3] = max requests allowed in the window
# ARGV[4] = unique member id for this request (if allowed)
#
# Returns: {allowed (1/0), current_count, limit, oldest_timestamp_or_now}
RATE_LIMIT_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

local window_start = now - window

-- 1. remove timestamps outside the window
redis.call("ZREMRANGEBYSCORE", key, 0, window_start)

-- 2. count requests currently inside the window
local current_count = redis.call("ZCARD", key)

-- 3. decide
if current_count >= limit then
    -- find the oldest entry to compute a real retry-after, not a guess
    local oldest = redis.call("ZRANGE", key, 0, 0, "WITHSCORES")
    local oldest_ts = now
    if oldest[2] then
        oldest_ts = tonumber(oldest[2])
    end
    return {0, current_count, limit, oldest_ts}
end

-- 4. record the new request
redis.call("ZADD", key, now, member)

-- 5. set/refresh expiration so idle keys clean themselves up
redis.call("EXPIRE", key, window)

return {1, current_count + 1, limit, now}
"""