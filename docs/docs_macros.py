def define_env(env):
    """Define variables and macros for the site"""
    def issue_link(number):
        return f'[#{number}](https://github.com/cheginit/pywbt/issues/{number})'
    
    def commit_link(hash):
        return f'[{hash[:7]}](https://github.com/cheginit/pywbt/commit/{hash})'

    env.macro(issue_link, 'issue')
    env.macro(commit_link, 'commit')