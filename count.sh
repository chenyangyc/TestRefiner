git log --since="2 days ago" --numstat --pretty="%H" -- '*.py' | awk '
BEGIN { 
    commits = 0; 
    added = 0; 
    deleted = 0; 
}
{
    if ($0 ~ /^[0-9a-f]{40}$/) {
        commits++;
    } else if (NF == 3) {
        added += $1;
        deleted += $2;
    }
}
END {
    print "Commits:", commits;
    print "Lines added:", added;
    print "Lines deleted:", deleted;
}'

