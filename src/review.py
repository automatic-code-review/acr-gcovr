import automatic_code_review_commons as commons

def review(config):
    path_target = config['path_target']
    path_source = config['path_source']

    merge = config['merge']
    project_id = merge['project_id']
    merge_request_id = merge['merge_request_id']
    
    comments = []
    
    # TODO IMPLEMENTAR EXTENSION
    #  O OBJETO DE COMENTARIO DEVE POSSUIR O SEGUINTE FORMATO
    #  commons.comment_create(
    #     comment_id=commons.comment_generate_id( "" ),
    #     comment_path="",
    #     comment_description="",
    #     comment_snipset=True,
    #     comment_end_line=1,
    #     comment_start_line=1,
    #     comment_language="",
    # )

    return comments
